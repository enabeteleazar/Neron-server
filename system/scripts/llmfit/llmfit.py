#!/usr/bin/env python3
"""
llmfit.py — Python rewrite of llmfit (Rust)
Détecte le hardware, score les modèles LLM et recommande ceux qui tournent sur votre machine.

Usage:
    python llmfit.py                        # Affiche tous les modèles classés
    python llmfit.py --fit                  # Seulement les modèles exécutables
    python llmfit.py --perfect              # Seulement les modèles "Perfect"
    python llmfit.py system                 # Infos hardware
    python llmfit.py list                   # Liste tous les modèles
    python llmfit.py search "llama 8b"      # Rechercher un modèle
    python llmfit.py info "Mistral-7B"      # Détail d'un modèle
    python llmfit.py recommend              # Top 5 recommandations (JSON)
    python llmfit.py recommend --use-case coding --limit 3
    python llmfit.py plan "Qwen/Qwen3-4B"  # Estimer le hardware nécessaire
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional

# ─── Chemin vers la base de données des modèles ──────────────────────────────
_SCRIPT_DIR = Path(__file__).parent
_DATA_PATHS = [
    _SCRIPT_DIR / "hf_models.json",
    _SCRIPT_DIR / "../data/hf_models.json",
    Path(__file__).parent.parent / "data" / "hf_models.json",
]

# ─────────────────────────────────────────────────────────────────────────────
# Quantization helpers
# ─────────────────────────────────────────────────────────────────────────────

QUANT_HIERARCHY = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K"]
MLX_QUANT_HIERARCHY = ["mlx-8bit", "mlx-4bit"]


def quant_bpp(quant: str) -> float:
    """Bytes per parameter for a given quantization."""
    table = {
        "F32": 4.0, "F16": 2.0, "BF16": 2.0,
        "Q8_0": 1.05, "Q6_K": 0.80, "Q5_K_M": 0.68,
        "Q4_K_M": 0.58, "Q4_0": 0.58, "Q3_K_M": 0.48, "Q2_K": 0.37,
        "mlx-4bit": 0.55, "mlx-8bit": 1.0,
        "AWQ-4bit": 0.5, "AWQ-8bit": 1.0,
        "GPTQ-Int4": 0.5, "GPTQ-Int8": 1.0,
    }
    return table.get(quant, 0.58)


def quant_bytes_per_param(quant: str) -> float:
    table = {
        "F16": 2.0, "BF16": 2.0, "Q8_0": 1.0, "Q6_K": 0.75,
        "Q5_K_M": 0.625, "Q4_K_M": 0.5, "Q4_0": 0.5, "Q3_K_M": 0.375,
        "Q2_K": 0.25, "mlx-4bit": 0.5, "mlx-8bit": 1.0,
        "AWQ-4bit": 0.5, "AWQ-8bit": 1.0, "GPTQ-Int4": 0.5, "GPTQ-Int8": 1.0,
    }
    return table.get(quant, 0.5)


def quant_speed_multiplier(quant: str) -> float:
    table = {
        "F16": 0.6, "BF16": 0.6, "Q8_0": 0.8, "Q6_K": 0.95, "Q5_K_M": 1.0,
        "Q4_K_M": 1.15, "Q4_0": 1.15, "Q3_K_M": 1.25, "Q2_K": 1.35,
        "mlx-4bit": 1.15, "mlx-8bit": 0.85,
        "AWQ-4bit": 1.2, "AWQ-8bit": 0.85, "GPTQ-Int4": 1.2, "GPTQ-Int8": 0.85,
    }
    return table.get(quant, 1.0)


def quant_quality_penalty(quant: str) -> float:
    table = {
        "F16": 0.0, "BF16": 0.0, "Q8_0": 0.0, "Q6_K": -1.0, "Q5_K_M": -2.0,
        "Q4_K_M": -5.0, "Q4_0": -5.0, "Q3_K_M": -8.0, "Q2_K": -12.0,
        "mlx-4bit": -4.0, "mlx-8bit": 0.0,
        "AWQ-4bit": -3.0, "AWQ-8bit": 0.0, "GPTQ-Int4": -3.0, "GPTQ-Int8": 0.0,
    }
    return table.get(quant, -5.0)


# ─────────────────────────────────────────────────────────────────────────────
# Hardware detection
# ─────────────────────────────────────────────────────────────────────────────

class GpuBackend(Enum):
    CUDA = "CUDA"
    METAL = "Metal"
    ROCM = "ROCm"
    VULKAN = "Vulkan"
    SYCL = "SYCL"
    CPU_ARM = "CPU (ARM)"
    CPU_X86 = "CPU (x86)"
    ASCEND = "NPU (Ascend)"


@dataclass
class GpuInfo:
    name: str
    vram_gb: Optional[float]
    backend: GpuBackend
    count: int = 1
    unified_memory: bool = False


@dataclass
class SystemSpecs:
    total_ram_gb: float
    available_ram_gb: float
    total_cpu_cores: int
    cpu_name: str
    has_gpu: bool
    gpu_vram_gb: Optional[float]
    total_gpu_vram_gb: Optional[float]
    gpu_name: Optional[str]
    gpu_count: int
    unified_memory: bool
    backend: GpuBackend
    gpus: list[GpuInfo] = field(default_factory=list)

    def display(self) -> None:
        print("\n=== Spécifications système ===")
        print(f"CPU: {self.cpu_name} ({self.total_cpu_cores} cœurs)")
        print(f"RAM totale:      {self.total_ram_gb:.2f} GB")
        print(f"RAM disponible:  {self.available_ram_gb:.2f} GB")
        print(f"Backend:         {self.backend.value}")
        if not self.gpus:
            print("GPU: Non détecté")
        else:
            for i, gpu in enumerate(self.gpus):
                prefix = f"GPU {i+1}: " if len(self.gpus) > 1 else "GPU: "
                vram = gpu.vram_gb or 0.0
                if gpu.unified_memory:
                    print(f"{prefix}{gpu.name} (mémoire unifiée, {vram:.2f} GB partagé, {gpu.backend.value})")
                elif vram > 0:
                    if gpu.count > 1:
                        print(f"{prefix}{gpu.name} x{gpu.count} ({vram:.2f} GB VRAM chacun = {vram*gpu.count:.0f} GB total, {gpu.backend.value})")
                    else:
                        print(f"{prefix}{gpu.name} ({vram:.2f} GB VRAM, {gpu.backend.value})")
                else:
                    print(f"{prefix}{gpu.name} (VRAM inconnue, {gpu.backend.value})")
        print()


def _run(cmd: list[str], timeout: int = 5) -> Optional[str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return None


def _estimate_vram_from_name(name: str) -> float:
    lower = name.lower()
    checks = [
        ("5090", 32), ("5080", 16), ("5070 ti", 16), ("5070", 12), ("5060 ti", 16), ("5060", 8),
        ("4090", 24), ("4080", 16), ("4070 ti", 12), ("4070", 12), ("4060 ti", 16), ("4060", 8),
        ("3090", 24), ("3080 ti", 12), ("3080", 10), ("3070", 8), ("3060 ti", 8), ("3060", 12),
        ("h100", 80), ("a100", 80), ("l40", 48), ("a10", 24), ("t4", 16),
        ("gb10", 128), ("gb20", 128),
        ("7900 xtx", 24), ("7900", 20), ("7800", 16), ("7700", 12), ("7600", 8),
        ("6900", 16), ("6800", 16), ("6700", 12), ("6600", 8),
    ]
    for keyword, vram in checks:
        if keyword in lower:
            return float(vram)
    if "rtx" in lower:
        return 8.0
    if "gtx" in lower:
        return 4.0
    if "rx " in lower or "radeon" in lower:
        return 8.0
    return 0.0


def gpu_memory_bandwidth_gbps(name: str) -> Optional[float]:
    """Return memory bandwidth in GB/s for a GPU name, or None if unknown."""
    lower = name.lower()
    table = [
        # NVIDIA RTX 50
        ("5090", 1792), ("5080", 960), ("5070 ti", 896), ("5070", 672),
        ("5060 ti", 448), ("5060", 256),
        # RTX 40
        ("4090", 1008), ("4080 super", 736), ("4080", 717),
        ("4070 ti super", 672), ("4070 ti", 504), ("4070 super", 504),
        ("4070", 504), ("4060 ti", 288), ("4060", 272),
        # RTX 30
        ("3090 ti", 1008), ("3090", 936), ("3080 ti", 912), ("3080", 760),
        ("3070 ti", 608), ("3070", 448), ("3060 ti", 448), ("3060", 360),
        # RTX 20
        ("2080 ti", 616), ("2080 super", 496), ("2080", 448),
        ("2070 super", 448), ("2070", 448), ("2060 super", 448), ("2060", 336),
        # GTX 16
        ("1660 ti", 288), ("1660 super", 336), ("1660", 192), ("1650 super", 192), ("1650", 128),
        # Data center NVIDIA
        ("h100 sxm", 3350), ("h200", 4800), ("h100", 2039),
        ("a100 sxm", 2039), ("a100", 1555),
        ("l40s", 864), ("l40", 864), (" l4", 300),
        ("a10g", 600), ("a10", 600), ("t4", 320),
        ("v100 sxm", 900), ("v100", 897),
        ("a6000", 768), ("a5000", 768), ("a4000", 448),
        # AMD RDNA4
        ("9070 xt", 624), ("9070", 488),
        # AMD RDNA3
        ("7900 xtx", 960), ("7900 xt", 800), ("7900 gre", 576),
        ("7800 xt", 624), ("7700 xt", 432), ("7600", 288),
        # AMD RDNA2
        ("6950 xt", 576), ("6900 xt", 512), ("6800 xt", 512), ("6800", 512),
        ("6700 xt", 384), ("6600 xt", 256), ("6600", 224),
        # AMD CDNA
        ("mi300x", 5300), ("mi300", 5300), ("mi250x", 3277),
        ("mi250", 3277), ("mi210", 1638), ("mi100", 1229),
        # Apple Silicon
        ("m4 ultra", 819), ("m4 max", 546), ("m4 pro", 273), ("m4", 120),
        ("m3 ultra", 800), ("m3 max", 400), ("m3 pro", 150), ("m3", 100),
        ("m2 ultra", 800), ("m2 max", 400), ("m2 pro", 200), ("m2", 100),
        ("m1 ultra", 800), ("m1 max", 400), ("m1 pro", 200), ("m1", 68),
    ]
    for keyword, bw in table:
        if keyword in lower:
            return float(bw)
    return None


def _detect_nvidia_gpus() -> list[GpuInfo]:
    output = _run(["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"])
    if not output:
        return []
    gpus_raw: dict[str, tuple[int, float]] = {}
    for line in output.strip().splitlines():
        parts = line.split(",", 1)
        if len(parts) < 2:
            continue
        name = parts[1].strip() or "NVIDIA GPU"
        try:
            vram_mb = float(parts[0].strip())
        except ValueError:
            vram_mb = _estimate_vram_from_name(name) * 1024
        if vram_mb <= 0:
            vram_mb = _estimate_vram_from_name(name) * 1024
        if name in gpus_raw:
            count, existing_vram = gpus_raw[name]
            gpus_raw[name] = (count + 1, max(existing_vram, vram_mb))
        else:
            gpus_raw[name] = (1, vram_mb)
    return [
        GpuInfo(name=name, vram_gb=vram_mb / 1024.0, backend=GpuBackend.CUDA, count=count)
        for name, (count, vram_mb) in gpus_raw.items()
    ]


def _detect_amd_gpu() -> Optional[GpuInfo]:
    output = _run(["rocm-smi", "--showmeminfo", "vram"])
    if not output:
        return None
    vram_bytes = 0
    for line in output.splitlines():
        lower = line.lower()
        if "total" in lower and "used" not in lower:
            nums = [int(w) for w in line.split() if w.isdigit()]
            if nums:
                vram_bytes = max(vram_bytes, nums[-1])
    name_out = _run(["rocm-smi", "--showproductname"]) or ""
    name = "AMD GPU"
    for line in name_out.splitlines():
        if "card series" in line.lower() or "card model" in line.lower():
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[1].strip():
                name = parts[1].strip()
                break
    vram_gb = vram_bytes / (1024 ** 3) if vram_bytes > 0 else _estimate_vram_from_name(name)
    return GpuInfo(name=name, vram_gb=vram_gb or None, backend=GpuBackend.ROCM)


def _detect_apple_gpu(total_ram_gb: float) -> Optional[GpuInfo]:
    if platform.system() != "Darwin":
        return None
    output = _run(["system_profiler", "SPDisplaysDataType"])
    if not output:
        return None
    is_apple = any(
        "apple m" in line.lower() or "apple gpu" in line.lower()
        for line in output.splitlines()
    )
    if not is_apple:
        return None
    cpu_name = platform.processor() or platform.machine()
    # Try to get actual chip name
    chip_out = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    name = chip_out.strip() if chip_out else "Apple Silicon"
    return GpuInfo(name=name, vram_gb=total_ram_gb, backend=GpuBackend.METAL, unified_memory=True)


def _detect_all_gpus(total_ram_gb: float, cpu_name: str) -> list[GpuInfo]:
    gpus: list[GpuInfo] = []

    # NVIDIA
    nvidia = _detect_nvidia_gpus()
    gpus.extend(nvidia)

    # AMD
    if not any(g.backend == GpuBackend.ROCM for g in gpus):
        amd = _detect_amd_gpu()
        if amd:
            gpus.append(amd)

    # Apple Silicon
    apple = _detect_apple_gpu(total_ram_gb)
    if apple:
        if not any(g.backend == GpuBackend.METAL for g in gpus):
            gpus.append(apple)

    # Sort by VRAM descending
    gpus.sort(key=lambda g: g.vram_gb or 0.0, reverse=True)
    return gpus


def _get_total_ram() -> tuple[float, float]:
    """Returns (total_gb, available_gb)."""
    system = platform.system()
    if system == "Linux":
        try:
            meminfo = Path("/proc/meminfo").read_text()
            total_kb = available_kb = 0
            for line in meminfo.splitlines():
                if line.startswith("MemTotal:"):
                    total_kb = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    available_kb = int(line.split()[1])
            return total_kb / (1024 ** 2), available_kb / (1024 ** 2)
        except Exception:
            pass
    elif system == "Darwin":
        try:
            import resource
            total_out = _run(["sysctl", "-n", "hw.memsize"])
            total_bytes = int(total_out.strip()) if total_out else 0
            total_gb = total_bytes / (1024 ** 3)
            # vm_stat for available
            vm_out = _run(["vm_stat"])
            if vm_out:
                page_size = 16384
                m = re.search(r"page size of (\d+)", vm_out)
                if m:
                    page_size = int(m.group(1))
                pages = {"free": 0, "inactive": 0, "purgeable": 0}
                for line in vm_out.splitlines():
                    for key in pages:
                        if f"Pages {key}" in line:
                            nums = re.findall(r"\d+", line)
                            if nums:
                                pages[key] = int(nums[-1])
                available_bytes = (pages["free"] + pages["inactive"] + pages["purgeable"]) * page_size
                available_gb = available_bytes / (1024 ** 3)
                return total_gb, available_gb
        except Exception:
            pass
    elif system == "Windows":
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return stat.ullTotalPhys / (1024 ** 3), stat.ullAvailPhys / (1024 ** 3)
        except Exception:
            pass

    # Fallback: psutil if available
    try:
        import psutil
        vm = psutil.virtual_memory()
        return vm.total / (1024 ** 3), vm.available / (1024 ** 3)
    except ImportError:
        pass

    return 8.0, 6.0  # Default fallback


def _get_cpu_cores() -> int:
    return os.cpu_count() or 4


def _get_cpu_name() -> str:
    system = platform.system()
    if system == "Linux":
        try:
            cpuinfo = Path("/proc/cpuinfo").read_text()
            for line in cpuinfo.splitlines():
                if "model name" in line.lower():
                    return line.split(":", 1)[1].strip()
        except Exception:
            pass
    elif system == "Darwin":
        out = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if out:
            return out.strip()
    elif system == "Windows":
        out = _run(["wmic", "cpu", "get", "Name", "/value"])
        if out:
            for line in out.splitlines():
                if "Name=" in line:
                    return line.split("=", 1)[1].strip()
    return platform.processor() or platform.machine() or "CPU inconnu"


def detect_system(memory_override_gb: Optional[float] = None) -> SystemSpecs:
    total_ram_gb, available_ram_gb = _get_total_ram()
    total_cpu_cores = _get_cpu_cores()
    cpu_name = _get_cpu_name()

    gpus = _detect_all_gpus(total_ram_gb, cpu_name)

    primary = gpus[0] if gpus else None
    has_gpu = bool(gpus)
    gpu_vram_gb = primary.vram_gb if primary else None
    total_gpu_vram_gb = (primary.vram_gb * primary.count) if primary and primary.vram_gb else None
    gpu_name = primary.name if primary else None
    gpu_count = primary.count if primary else 0
    unified_memory = primary.unified_memory if primary else False

    # Determine backend
    if primary:
        backend = primary.backend
    elif "aarch64" in platform.machine().lower() or "arm" in platform.machine().lower():
        backend = GpuBackend.CPU_ARM
    else:
        backend = GpuBackend.CPU_X86

    specs = SystemSpecs(
        total_ram_gb=total_ram_gb,
        available_ram_gb=available_ram_gb,
        total_cpu_cores=total_cpu_cores,
        cpu_name=cpu_name,
        has_gpu=has_gpu,
        gpu_vram_gb=gpu_vram_gb,
        total_gpu_vram_gb=total_gpu_vram_gb,
        gpu_name=gpu_name,
        gpu_count=gpu_count,
        unified_memory=unified_memory,
        backend=backend,
        gpus=gpus,
    )

    if memory_override_gb is not None:
        specs = _apply_gpu_memory_override(specs, memory_override_gb)

    return specs


def _apply_gpu_memory_override(specs: SystemSpecs, vram_gb: float) -> SystemSpecs:
    if not specs.gpus:
        backend = GpuBackend.METAL if "apple" in specs.cpu_name.lower() else GpuBackend.CUDA
        specs.gpus.append(GpuInfo(name="GPU (override)", vram_gb=vram_gb, backend=backend))
        specs.has_gpu = True
        specs.backend = backend
    else:
        specs.gpus[0].vram_gb = vram_gb
    specs.gpu_vram_gb = vram_gb
    specs.total_gpu_vram_gb = vram_gb * (specs.gpus[0].count if specs.gpus else 1)
    specs.gpu_name = specs.gpus[0].name
    specs.has_gpu = True
    return specs


# ─────────────────────────────────────────────────────────────────────────────
# Model database
# ─────────────────────────────────────────────────────────────────────────────

class UseCase(Enum):
    GENERAL = "General"
    CODING = "Coding"
    REASONING = "Reasoning"
    CHAT = "Chat"
    MULTIMODAL = "Multimodal"
    EMBEDDING = "Embedding"

    @classmethod
    def from_model(cls, name: str, use_case_str: str) -> "UseCase":
        name_l = name.lower()
        uc_l = use_case_str.lower()
        if "embedding" in uc_l or "embed" in name_l or "bge" in name_l:
            return cls.EMBEDDING
        if "code" in name_l or "code" in uc_l:
            return cls.CODING
        if "vision" in uc_l or "multimodal" in uc_l:
            return cls.MULTIMODAL
        if "reason" in uc_l or "chain-of-thought" in uc_l or "deepseek-r1" in name_l:
            return cls.REASONING
        if "chat" in uc_l or "instruction" in uc_l:
            return cls.CHAT
        return cls.GENERAL


@dataclass
class LlmModel:
    name: str
    provider: str
    parameter_count: str
    parameters_raw: Optional[int]
    min_ram_gb: float
    recommended_ram_gb: float
    min_vram_gb: Optional[float]
    quantization: str
    context_length: int
    use_case: str
    is_moe: bool = False
    num_experts: Optional[int] = None
    active_experts: Optional[int] = None
    active_parameters: Optional[int] = None
    release_date: Optional[str] = None
    gguf_sources: list = field(default_factory=list)
    capabilities: list = field(default_factory=list)
    format: str = "gguf"

    def params_b(self) -> float:
        if self.parameters_raw:
            return self.parameters_raw / 1e9
        s = self.parameter_count.upper().strip()
        if s.endswith("B"):
            try:
                return float(s[:-1])
            except ValueError:
                pass
        if s.endswith("M"):
            try:
                return float(s[:-1]) / 1000.0
            except ValueError:
                pass
        if s.endswith("K"):
            try:
                return float(s[:-1]) / 1e6
            except ValueError:
                pass
        return 7.0

    def is_mlx_model(self) -> bool:
        return "-mlx-" in self.name.lower() or self.name.lower().endswith("-mlx")

    def is_prequantized(self) -> bool:
        return self.format.lower() in ("awq", "gptq")

    def estimate_memory_gb(self, quant: str, ctx: int) -> float:
        bpp = quant_bpp(quant)
        params = self.params_b()
        model_mem = params * bpp
        kv_cache = 0.000008 * params * ctx
        overhead = 0.5
        return model_mem + kv_cache + overhead

    def best_quant_for_budget(self, budget_gb: float, ctx: int,
                               hierarchy: Optional[list[str]] = None) -> Optional[tuple[str, float]]:
        hierarchy = hierarchy or QUANT_HIERARCHY
        for q in hierarchy:
            mem = self.estimate_memory_gb(q, ctx)
            if mem <= budget_gb:
                return (q, mem)
        # Try half context
        half_ctx = ctx // 2
        if half_ctx >= 1024:
            for q in hierarchy:
                mem = self.estimate_memory_gb(q, half_ctx)
                if mem <= budget_gb:
                    return (q, mem)
        return None

    def moe_active_vram_gb(self) -> Optional[float]:
        if not self.is_moe or not self.active_parameters:
            return None
        bpp = quant_bpp(self.quantization)
        size_gb = (self.active_parameters * bpp) / (1024 ** 3)
        return max(size_gb * 1.1, 0.5)

    def moe_offloaded_ram_gb(self) -> Optional[float]:
        if not self.is_moe or not self.active_parameters or not self.parameters_raw:
            return None
        inactive = max(self.parameters_raw - self.active_parameters, 0)
        bpp = quant_bpp(self.quantization)
        return (inactive * bpp) / (1024 ** 3)


def load_model_database(data_path: Optional[Path] = None) -> list[LlmModel]:
    # Find data file
    if data_path and data_path.exists():
        paths_to_try = [data_path]
    else:
        paths_to_try = _DATA_PATHS

    for p in paths_to_try:
        if p.exists():
            data_path = p
            break
    else:
        print("⚠️  Base de données introuvable (hf_models.json). Essayez de la placer dans le même répertoire.",
              file=sys.stderr)
        return []

    with open(data_path, encoding="utf-8") as f:
        entries = json.load(f)

    models = []
    for e in entries:
        model = LlmModel(
            name=e.get("name", ""),
            provider=e.get("provider", ""),
            parameter_count=e.get("parameter_count", "7B"),
            parameters_raw=e.get("parameters_raw"),
            min_ram_gb=e.get("min_ram_gb", 4.0),
            recommended_ram_gb=e.get("recommended_ram_gb", 8.0),
            min_vram_gb=e.get("min_vram_gb"),
            quantization=e.get("quantization", "Q4_K_M"),
            context_length=e.get("context_length", 4096),
            use_case=e.get("use_case", "General"),
            is_moe=e.get("is_moe", False),
            num_experts=e.get("num_experts"),
            active_experts=e.get("active_experts"),
            active_parameters=e.get("active_parameters"),
            release_date=e.get("release_date"),
            gguf_sources=e.get("gguf_sources", []),
            capabilities=e.get("capabilities", []),
            format=e.get("format", "gguf"),
        )
        models.append(model)
    return models


# ─────────────────────────────────────────────────────────────────────────────
# Fit analysis & scoring
# ─────────────────────────────────────────────────────────────────────────────

class FitLevel(Enum):
    PERFECT = "Perfect"
    GOOD = "Good"
    MARGINAL = "Marginal"
    TOO_TIGHT = "Too Tight"


class RunMode(Enum):
    GPU = "GPU"
    MOE_OFFLOAD = "MoE"
    CPU_OFFLOAD = "CPU+GPU"
    CPU_ONLY = "CPU"


class InferenceRuntime(Enum):
    LLAMACPP = "llama.cpp"
    MLX = "MLX"
    VLLM = "vLLM"


@dataclass
class ScoreComponents:
    quality: float
    speed: float
    fit: float
    context: float


@dataclass
class ModelFit:
    model: LlmModel
    fit_level: FitLevel
    run_mode: RunMode
    memory_required_gb: float
    memory_available_gb: float
    utilization_pct: float
    notes: list[str]
    moe_offloaded_gb: Optional[float]
    score: float
    score_components: ScoreComponents
    estimated_tps: float
    best_quant: str
    use_case: UseCase
    runtime: InferenceRuntime
    installed: bool = False

    def fit_emoji(self) -> str:
        return {"Perfect": "🟢", "Good": "🟡", "Marginal": "🟠", "Too Tight": "🔴"}[self.fit_level.value]

    def to_dict(self) -> dict:
        return {
            "name": self.model.name,
            "provider": self.model.provider,
            "params": self.model.parameter_count,
            "score": round(self.score, 1),
            "fit": self.fit_level.value,
            "run_mode": self.run_mode.value,
            "runtime": self.runtime.value,
            "best_quant": self.best_quant,
            "estimated_tps": round(self.estimated_tps, 1),
            "memory_required_gb": round(self.memory_required_gb, 2),
            "utilization_pct": round(self.utilization_pct, 1),
            "use_case": self.use_case.value,
            "context_length": self.model.context_length,
            "release_date": self.model.release_date,
            "notes": self.notes,
        }


def _score_fit(mem_required: float, mem_available: float,
               recommended: float, run_mode: RunMode) -> FitLevel:
    if mem_required > mem_available:
        return FitLevel.TOO_TIGHT
    if run_mode == RunMode.GPU:
        if recommended <= mem_available:
            return FitLevel.PERFECT
        if mem_available >= mem_required * 1.2:
            return FitLevel.GOOD
        return FitLevel.MARGINAL
    if run_mode in (RunMode.MOE_OFFLOAD, RunMode.CPU_OFFLOAD):
        if mem_available >= mem_required * 1.2:
            return FitLevel.GOOD
        return FitLevel.MARGINAL
    return FitLevel.MARGINAL  # CPU_ONLY always Marginal


def _estimate_tps(model: LlmModel, quant: str, system: SystemSpecs,
                  run_mode: RunMode, runtime: InferenceRuntime) -> float:
    params = max(
        ((model.active_parameters or 0) / 1e9 if model.is_moe and model.active_parameters else model.params_b()),
        0.1
    )

    # Bandwidth-based estimation
    gpu_name = system.gpu_name or ""
    bw = gpu_memory_bandwidth_gbps(gpu_name)
    if bw and run_mode != RunMode.CPU_ONLY:
        model_gb = params * quant_bytes_per_param(quant)
        efficiency = 0.55
        raw_tps = (bw / model_gb) * efficiency
        mode_factor = {RunMode.GPU: 1.0, RunMode.MOE_OFFLOAD: 0.8, RunMode.CPU_OFFLOAD: 0.5}.get(run_mode, 1.0)
        return max(raw_tps * mode_factor, 0.1)

    # Fallback fixed-constant
    K_table = {
        (GpuBackend.METAL, InferenceRuntime.MLX): 250.0,
        (GpuBackend.METAL, InferenceRuntime.LLAMACPP): 160.0,
        (GpuBackend.CUDA, None): 220.0,
        (GpuBackend.ROCM, None): 180.0,
        (GpuBackend.VULKAN, None): 150.0,
        (GpuBackend.SYCL, None): 100.0,
        (GpuBackend.CPU_ARM, None): 90.0,
        (GpuBackend.CPU_X86, None): 70.0,
        (GpuBackend.ASCEND, None): 390.0,
    }
    k = K_table.get((system.backend, runtime), K_table.get((system.backend, None), 70.0))
    base = (k / params) * quant_speed_multiplier(quant)
    if system.total_cpu_cores >= 8:
        base *= 1.1
    if run_mode == RunMode.MOE_OFFLOAD:
        base *= 0.8
    elif run_mode == RunMode.CPU_OFFLOAD:
        base *= 0.5
    elif run_mode == RunMode.CPU_ONLY:
        cpu_k = 90.0 if "arm" in platform.machine().lower() else 70.0
        base = (cpu_k / params) * quant_speed_multiplier(quant)
        if system.total_cpu_cores >= 8:
            base *= 1.1
    return max(base, 0.1)


def _quality_score(model: LlmModel, quant: str, use_case: UseCase) -> float:
    params = model.params_b()
    if params < 1.0: base = 30.0
    elif params < 3.0: base = 45.0
    elif params < 7.0: base = 60.0
    elif params < 10.0: base = 75.0
    elif params < 20.0: base = 82.0
    elif params < 40.0: base = 89.0
    else: base = 95.0

    name_l = model.name.lower()
    family_bump = 2.0 if "qwen" in name_l else \
                  3.0 if "deepseek" in name_l else \
                  2.0 if "llama" in name_l else \
                  1.0 if "mistral" in name_l or "mixtral" in name_l else \
                  1.0 if "gemma" in name_l else 0.0

    penalty = quant_quality_penalty(quant)

    task_bump = 0.0
    if use_case == UseCase.CODING and any(k in name_l for k in ("code", "starcoder", "wizard")):
        task_bump = 6.0
    elif use_case == UseCase.REASONING and params >= 13.0:
        task_bump = 5.0
    elif use_case == UseCase.MULTIMODAL and ("vision" in name_l or "vision" in model.use_case.lower()):
        task_bump = 6.0

    return max(0.0, min(100.0, base + family_bump + penalty + task_bump))


def _speed_score(tps: float, use_case: UseCase) -> float:
    target = 200.0 if use_case == UseCase.EMBEDDING else \
             25.0 if use_case == UseCase.REASONING else 40.0
    return min(100.0, (tps / target) * 100.0)


def _fit_score(required: float, available: float) -> float:
    if available <= 0 or required > available:
        return 0.0
    ratio = required / available
    if ratio <= 0.5:
        return 60.0 + (ratio / 0.5) * 40.0
    if ratio <= 0.8:
        return 100.0
    if ratio <= 0.9:
        return 70.0
    return 50.0


def _context_score(model: LlmModel, use_case: UseCase) -> float:
    target = 512 if use_case == UseCase.EMBEDDING else \
             8192 if use_case in (UseCase.CODING, UseCase.REASONING) else 4096
    if model.context_length >= target:
        return 100.0
    if model.context_length >= target // 2:
        return 70.0
    return 30.0


def _weighted_score(sc: ScoreComponents, use_case: UseCase) -> float:
    weights = {
        UseCase.GENERAL: (0.45, 0.30, 0.15, 0.10),
        UseCase.CODING: (0.50, 0.20, 0.15, 0.15),
        UseCase.REASONING: (0.55, 0.15, 0.15, 0.15),
        UseCase.CHAT: (0.40, 0.35, 0.15, 0.10),
        UseCase.MULTIMODAL: (0.50, 0.20, 0.15, 0.15),
        UseCase.EMBEDDING: (0.30, 0.40, 0.20, 0.10),
    }
    wq, ws, wf, wc = weights.get(use_case, (0.45, 0.30, 0.15, 0.10))
    raw = sc.quality * wq + sc.speed * ws + sc.fit * wf + sc.context * wc
    return round(raw * 10) / 10


def _cpu_path(model: LlmModel, system: SystemSpecs, runtime: InferenceRuntime,
              ctx: int, notes: list) -> tuple[RunMode, float, float]:
    notes.append("CPU-only : modèle chargé en RAM")
    if model.is_moe:
        notes.append("Architecture MoE, mais l'offloading d'experts nécessite un GPU")
        return RunMode.CPU_ONLY, model.min_ram_gb, system.available_ram_gb

    hierarchy = MLX_QUANT_HIERARCHY if runtime == InferenceRuntime.MLX else QUANT_HIERARCHY
    result = model.best_quant_for_budget(system.available_ram_gb, ctx, hierarchy)
    if result:
        return RunMode.CPU_ONLY, result[1], system.available_ram_gb
    return RunMode.CPU_ONLY, model.estimate_memory_gb(model.quantization, ctx), system.available_ram_gb


def _moe_offload_path(model: LlmModel, system: SystemSpecs, system_vram: float,
                      total_vram: float, runtime: InferenceRuntime, notes: list) -> tuple[RunMode, float, float]:
    hierarchy = MLX_QUANT_HIERARCHY if runtime == InferenceRuntime.MLX else QUANT_HIERARCHY
    for quant in hierarchy:
        if not model.is_moe or not model.active_parameters or not model.parameters_raw:
            continue
        bpp = quant_bpp(quant)
        active_params = model.active_parameters
        total_params = model.parameters_raw
        moe_vram = max((active_params * bpp) / (1024 ** 3) * 1.1, 0.5)
        inactive_params = max(total_params - active_params, 0)
        offloaded_ram = (inactive_params * bpp) / (1024 ** 3)
        if moe_vram <= system_vram and offloaded_ram <= system.available_ram_gb:
            notes.append(f"MoE: {model.active_experts}/{model.num_experts} experts actifs ({moe_vram:.1f} GB VRAM) à {quant}")
            notes.append(f"Experts inactifs offloadés en RAM ({offloaded_ram:.1f} GB)")
            return RunMode.MOE_OFFLOAD, moe_vram, system_vram

    # Fallback
    if model.min_ram_gb <= system.available_ram_gb:
        notes.append("MoE: VRAM insuffisante, déversement en RAM")
        return RunMode.CPU_OFFLOAD, model.min_ram_gb, system.available_ram_gb

    return RunMode.GPU, total_vram, system_vram


def analyze_model(model: LlmModel, system: SystemSpecs,
                  context_limit: Optional[int] = None) -> ModelFit:
    notes: list[str] = []
    estimation_ctx = min(context_limit, model.context_length) if context_limit else model.context_length
    if context_limit and context_limit < model.context_length:
        notes.append(f"Contexte plafonné pour estimation: {model.context_length} → {estimation_ctx} tokens")

    use_case = UseCase.from_model(model.name, model.use_case)
    min_vram = model.min_vram_gb or model.min_ram_gb
    default_mem = model.estimate_memory_gb(model.quantization, estimation_ctx)

    # Determine runtime
    if model.is_prequantized():
        runtime = InferenceRuntime.VLLM
    elif system.backend == GpuBackend.METAL and system.unified_memory:
        runtime = InferenceRuntime.MLX
    else:
        runtime = InferenceRuntime.LLAMACPP

    hierarchy = MLX_QUANT_HIERARCHY if runtime == InferenceRuntime.MLX else QUANT_HIERARCHY

    def choose_quant(budget: float):
        return model.best_quant_for_budget(budget, estimation_ctx, hierarchy)

    # Determine run path
    if system.has_gpu:
        if system.unified_memory and system.gpu_vram_gb:
            pool = system.gpu_vram_gb
            notes.append("Mémoire unifiée : GPU et CPU partagent le même pool")
            if model.is_moe:
                run_mode, mem_req, mem_avail = RunMode.GPU, min_vram, pool
            else:
                result = choose_quant(pool)
                mem_req = result[1] if result else default_mem
                run_mode, mem_avail = RunMode.GPU, pool
        elif system.total_gpu_vram_gb:
            vram = system.total_gpu_vram_gb
            if model.is_moe and min_vram <= vram:
                notes.append("GPU: modèle MoE chargé en VRAM")
                run_mode, mem_req, mem_avail = RunMode.GPU, min_vram, vram
            elif model.is_moe:
                run_mode, mem_req, mem_avail = _moe_offload_path(model, system, vram, min_vram, runtime, notes)
            else:
                result = choose_quant(vram)
                if result:
                    notes.append("GPU: modèle chargé en VRAM")
                    run_mode, mem_req, mem_avail = RunMode.GPU, result[1], vram
                else:
                    result = choose_quant(system.available_ram_gb)
                    if result:
                        notes.append("GPU: VRAM insuffisante, déversement en RAM")
                        notes.append("Les performances seront significativement réduites")
                        run_mode, mem_req, mem_avail = RunMode.CPU_OFFLOAD, result[1], system.available_ram_gb
                    else:
                        notes.append("VRAM et RAM insuffisantes")
                        run_mode, mem_req, mem_avail = RunMode.GPU, default_mem, vram
        else:
            notes.append("GPU détecté mais VRAM inconnue")
            run_mode, mem_req, mem_avail = _cpu_path(model, system, runtime, estimation_ctx, notes)
    else:
        run_mode, mem_req, mem_avail = _cpu_path(model, system, runtime, estimation_ctx, notes)

    fit_level = _score_fit(mem_req, mem_avail, model.recommended_ram_gb, run_mode)
    utilization_pct = (mem_req / mem_avail * 100.0) if mem_avail > 0 else float("inf")

    if run_mode == RunMode.CPU_ONLY:
        notes.append("Pas de GPU — l'inférence sera lente")

    moe_offloaded_gb = model.moe_offloaded_ram_gb() if run_mode == RunMode.MOE_OFFLOAD else None

    # Best quant selection
    if model.is_prequantized():
        best_quant = model.quantization
    else:
        budget = mem_avail
        result = model.best_quant_for_budget(budget, estimation_ctx, hierarchy)
        if result is None and runtime == InferenceRuntime.MLX:
            result = model.best_quant_for_budget(budget, estimation_ctx)
        best_quant = result[0] if result else model.quantization

    if best_quant != model.quantization:
        notes.append(f"Meilleure quantization pour ce hardware: {best_quant} (modèle par défaut: {model.quantization})")

    estimated_tps = _estimate_tps(model, best_quant, system, run_mode, runtime)
    if estimated_tps > 0:
        notes.append(f"Vitesse estimée: {estimated_tps:.1f} tok/s")

    # Score
    sc = ScoreComponents(
        quality=_quality_score(model, best_quant, use_case),
        speed=_speed_score(estimated_tps, use_case),
        fit=_fit_score(mem_req, mem_avail),
        context=_context_score(model, use_case),
    )
    score = _weighted_score(sc, use_case)

    return ModelFit(
        model=model,
        fit_level=fit_level,
        run_mode=run_mode,
        memory_required_gb=mem_req,
        memory_available_gb=mem_avail,
        utilization_pct=utilization_pct,
        notes=notes,
        moe_offloaded_gb=moe_offloaded_gb,
        score=score,
        score_components=sc,
        estimated_tps=estimated_tps,
        best_quant=best_quant,
        use_case=use_case,
        runtime=runtime,
    )


def rank_models(fits: list[ModelFit], installed_first: bool = False) -> list[ModelFit]:
    def sort_key(mf: ModelFit):
        runnable = mf.fit_level != FitLevel.TOO_TIGHT
        installed = mf.installed if installed_first else False
        return (installed, runnable, mf.score)
    return sorted(fits, key=sort_key, reverse=True)


def backend_compatible(model: LlmModel, system: SystemSpecs) -> bool:
    if model.is_mlx_model():
        return system.backend == GpuBackend.METAL and system.unified_memory
    if model.is_prequantized():
        return system.backend in (GpuBackend.CUDA, GpuBackend.ROCM)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Hardware planning
# ─────────────────────────────────────────────────────────────────────────────

def plan_model(model: LlmModel, context: int, quant: Optional[str],
               target_tps: Optional[float], system: SystemSpecs) -> dict:
    if context <= 0:
        raise ValueError("--context doit être > 0")
    if target_tps is not None and target_tps <= 0:
        raise ValueError("--target-tps doit être > 0")

    effective_quant = quant or model.quantization
    mem = model.estimate_memory_gb(effective_quant, context)

    paths = []
    for path_name, run_mode in [("GPU", RunMode.GPU), ("CPU offload", RunMode.CPU_OFFLOAD), ("CPU-only", RunMode.CPU_ONLY)]:
        tps = _estimate_tps(model, effective_quant, system, run_mode,
                             InferenceRuntime.MLX if system.backend == GpuBackend.METAL and system.unified_memory else InferenceRuntime.LLAMACPP)
        paths.append({
            "path": path_name,
            "memory_required_gb": round(mem, 2),
            "estimated_tps": round(tps, 1),
            "feasible": (run_mode == RunMode.CPU_ONLY) or system.has_gpu,
        })

    current_vram = system.total_gpu_vram_gb or 0
    add_vram_good = max(mem - current_vram, 0)
    add_vram_perfect = max(model.recommended_ram_gb - current_vram, 0)

    return {
        "model": model.name,
        "provider": model.provider,
        "context": context,
        "quantization": effective_quant,
        "target_tps": target_tps,
        "minimum": {"vram_gb": round(mem, 2), "ram_gb": round(mem, 2), "cpu_cores": 4},
        "recommended": {"vram_gb": round(model.recommended_ram_gb, 2), "ram_gb": round(model.recommended_ram_gb, 2), "cpu_cores": 8},
        "run_paths": paths,
        "upgrade_deltas": [
            {"resource": "vram_gb", "add_gb": round(add_vram_good, 1), "target_fit": "Good"},
            {"resource": "vram_gb", "add_gb": round(add_vram_perfect, 1), "target_fit": "Perfect"},
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI display helpers
# ─────────────────────────────────────────────────────────────────────────────

def _color(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def _bold(text: str) -> str:
    return _color(text, "1")


def _green(text: str) -> str:
    return _color(text, "32")


def _yellow(text: str) -> str:
    return _color(text, "33")


def _red(text: str) -> str:
    return _color(text, "31")


def _cyan(text: str) -> str:
    return _color(text, "36")


def _dim(text: str) -> str:
    return _color(text, "2")


FIT_COLORS = {
    "Perfect": _green,
    "Good": _yellow,
    "Marginal": lambda s: _color(s, "33"),
    "Too Tight": _red,
}


def print_fits_table(fits: list[ModelFit], n: Optional[int] = None) -> None:
    shown = fits[:n] if n else fits
    # Header
    cols = ["Score", "Modèle", "Params", "tok/s", "Quant", "Mode", "Mém%", "Ctx", "Fit", "Cas"]
    widths = [6, 40, 6, 6, 8, 8, 6, 7, 8, 10]
    header = "  ".join(f"{c:{w}}" for c, w in zip(cols, widths))
    print(_bold(header))
    print("─" * len(header))

    for mf in shown:
        fit_fn = FIT_COLORS.get(mf.fit_level.value, lambda s: s)
        too_tight = mf.fit_level == FitLevel.TOO_TIGHT

        name = mf.model.name
        if len(name) > 40:
            name = name[:37] + "..."

        mem_pct = f"{mf.utilization_pct:.0f}%" if mf.utilization_pct != float("inf") else "∞%"
        ctx = f"{mf.model.context_length // 1000}K"
        tps = f"{mf.estimated_tps:.0f}"
        score_str = f"{mf.score:.1f}"
        params_str = mf.model.parameter_count

        row = [score_str, name, params_str, tps, mf.best_quant[:8],
               mf.run_mode.value, mem_pct, ctx, mf.fit_level.value, mf.use_case.value]

        line = "  ".join(f"{v:{w}}" for v, w in zip(row, widths))
        if too_tight:
            print(_dim(line))
        else:
            print(fit_fn(line))

    print(f"\n{len(shown)} modèles affichés")


def print_model_info(mf: ModelFit) -> None:
    m = mf.model
    print(f"\n{'─'*60}")
    print(_bold(f"  {m.name}"))
    print(f"{'─'*60}")
    print(f"  Fournisseur:   {m.provider}")
    print(f"  Paramètres:    {m.parameter_count} ({m.params_b():.1f}B)")
    print(f"  Use case:      {m.use_case}")
    print(f"  Contexte:      {m.context_length:,} tokens")
    print(f"  Quantization:  {m.quantization}")
    print(f"  Format:        {m.format}")
    if m.release_date:
        print(f"  Sortie:        {m.release_date}")
    print()
    fit_fn = FIT_COLORS.get(mf.fit_level.value, lambda s: s)
    print(f"  Fit:           {fit_fn(mf.fit_emoji() + ' ' + mf.fit_level.value)}")
    print(f"  Mode:          {mf.run_mode.value}")
    print(f"  Runtime:       {mf.runtime.value}")
    print(f"  Meilleure Q.:  {mf.best_quant}")
    print(f"  Score:         {mf.score:.1f}/100")
    print(f"  Vitesse est.:  {mf.estimated_tps:.1f} tok/s")
    print(f"  Mémoire req.:  {mf.memory_required_gb:.2f} GB")
    print(f"  Mémoire dispo: {mf.memory_available_gb:.2f} GB")
    print(f"  Utilisation:   {mf.utilization_pct:.1f}%")
    if mf.notes:
        print(f"\n  Notes:")
        for note in mf.notes:
            print(f"    • {note}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Memory size parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_memory_size(s: str) -> Optional[float]:
    s = s.strip()
    if not s:
        return None
    m = re.match(r"^(\d+\.?\d*)(.*)$", s)
    if not m:
        return None
    value = float(m.group(1))
    suffix = m.group(2).strip().lower()
    if suffix in ("", "g", "gb", "gib"):
        return value
    if suffix in ("m", "mb", "mib"):
        return value / 1024.0
    if suffix in ("t", "tb", "tib"):
        return value * 1024.0
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="llmfit — Trouve les modèles LLM compatibles avec votre hardware",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--memory", "-m", help="Override VRAM (ex: 24G, 16384M)")
    parser.add_argument("--max-context", type=int, help="Plafonner le contexte pour l'estimation mémoire")
    parser.add_argument("--cli", action="store_true", help="Mode CLI (tableau classique)")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    parser.add_argument("--data", help="Chemin vers hf_models.json")

    subparsers = parser.add_subparsers(dest="command")

    # system
    subparsers.add_parser("system", help="Afficher les specs hardware")

    # list
    subparsers.add_parser("list", help="Lister tous les modèles")

    # search
    sp_search = subparsers.add_parser("search", help="Rechercher des modèles")
    sp_search.add_argument("query", help="Terme de recherche")

    # info
    sp_info = subparsers.add_parser("info", help="Détails d'un modèle")
    sp_info.add_argument("model", help="Nom ou partie du nom du modèle")

    # fit
    sp_fit = subparsers.add_parser("fit", help="Modèles compatibles avec votre hardware")
    sp_fit.add_argument("--perfect", "-p", action="store_true", help="Seulement les modèles Perfect")
    sp_fit.add_argument("-n", type=int, help="Nombre de modèles à afficher")

    # recommend
    sp_rec = subparsers.add_parser("recommend", help="Top recommandations")
    sp_rec.add_argument("--limit", type=int, default=5)
    sp_rec.add_argument("--use-case", choices=["general", "coding", "reasoning", "chat", "multimodal", "embedding"])

    # plan
    sp_plan = subparsers.add_parser("plan", help="Estimer le hardware nécessaire pour un modèle")
    sp_plan.add_argument("model", help="Nom du modèle")
    sp_plan.add_argument("--context", type=int, default=4096)
    sp_plan.add_argument("--quant", help="Quantization (ex: Q4_K_M)")
    sp_plan.add_argument("--target-tps", type=float, help="Cible tokens/s")

    args = parser.parse_args()

    # Parse memory override
    memory_override = None
    if args.memory:
        memory_override = parse_memory_size(args.memory)
        if memory_override is None:
            print(f"Erreur: impossible de parser --memory '{args.memory}'", file=sys.stderr)
            sys.exit(1)

    # Detect hardware
    system = detect_system(memory_override)

    # Load models
    data_path = Path(args.data) if getattr(args, "data", None) else None
    models = load_model_database(data_path)
    if not models and args.command not in ("system", None):
        print("Aucun modèle chargé.", file=sys.stderr)

    cmd = args.command

    # ── system ──────────────────────────────────────────────────────────────
    if cmd == "system":
        if args.json:
            data = {
                "cpu": system.cpu_name,
                "cpu_cores": system.total_cpu_cores,
                "total_ram_gb": round(system.total_ram_gb, 2),
                "available_ram_gb": round(system.available_ram_gb, 2),
                "backend": system.backend.value,
                "has_gpu": system.has_gpu,
                "gpu_name": system.gpu_name,
                "gpu_vram_gb": round(system.gpu_vram_gb, 2) if system.gpu_vram_gb else None,
                "unified_memory": system.unified_memory,
            }
            print(json.dumps(data, indent=2))
        else:
            system.display()
        return

    # ── list ────────────────────────────────────────────────────────────────
    if cmd == "list":
        for m in models:
            print(f"{m.name:60} {m.parameter_count:8} {m.use_case}")
        print(f"\n{len(models)} modèles au total")
        return

    # ── search ──────────────────────────────────────────────────────────────
    if cmd == "search":
        q = args.query.lower()
        results = [m for m in models if q in m.name.lower() or q in m.provider.lower()
                   or q in m.parameter_count.lower() or q in m.use_case.lower()]
        for m in results:
            print(f"{m.name:60} {m.parameter_count:8} {m.use_case}")
        print(f"\n{len(results)} résultat(s) pour '{args.query}'")
        return

    # ── info ────────────────────────────────────────────────────────────────
    if cmd == "info":
        q = args.model.lower()
        matches = [m for m in models if q in m.name.lower()]
        if not matches:
            print(f"Modèle '{args.model}' introuvable.")
            return
        target = next((m for m in matches if m.name.lower() == q), matches[0])
        mf = analyze_model(target, system, args.max_context)
        if args.json:
            print(json.dumps(mf.to_dict(), indent=2))
        else:
            print_model_info(mf)
        return

    # ── plan ────────────────────────────────────────────────────────────────
    if cmd == "plan":
        q = args.model.lower()
        matches = [m for m in models if q in m.name.lower()]
        if not matches:
            print(f"Modèle '{args.model}' introuvable.")
            return
        target = next((m for m in matches if m.name.lower() == q), matches[0])
        try:
            result = plan_model(target, args.context, args.quant, args.target_tps, system)
        except ValueError as e:
            print(f"Erreur: {e}", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n=== Plan hardware: {target.name} ===")
            print(f"  Contexte:      {args.context} tokens")
            print(f"  Quantization:  {args.quant or target.quantization}")
            print(f"  Mém. minimum:  {result['minimum']['vram_gb']:.2f} GB")
            print(f"  Mém. recomm.:  {result['recommended']['vram_gb']:.2f} GB")
            print("\n  Chemins d'exécution:")
            for p in result["run_paths"]:
                status = "✓" if p["feasible"] else "✗"
                print(f"    {status} {p['path']:12} {p['memory_required_gb']:.1f} GB   {p['estimated_tps']:.1f} tok/s")
            print("\n  Upgrades suggérés:")
            for d in result["upgrade_deltas"]:
                print(f"    • +{d['add_gb']:.1f} GB VRAM → {d['target_fit']}")
        return

    # ── Default: fit / recommend ──────────────────────────────────────────

    # Filter compatible models
    compatible = [m for m in models if backend_compatible(m, system)]

    # Analyze all
    print("Analyse en cours...", end="\r", file=sys.stderr)
    fits = [analyze_model(m, system, args.max_context) for m in compatible]
    fits = rank_models(fits)

    # ── recommend ──────────────────────────────────────────────────────────
    if cmd == "recommend":
        uc_filter = None
        if args.use_case:
            uc_map = {
                "general": UseCase.GENERAL, "coding": UseCase.CODING,
                "reasoning": UseCase.REASONING, "chat": UseCase.CHAT,
                "multimodal": UseCase.MULTIMODAL, "embedding": UseCase.EMBEDDING,
            }
            uc_filter = uc_map.get(args.use_case)

        runnable = [f for f in fits if f.fit_level != FitLevel.TOO_TIGHT]
        if uc_filter:
            runnable = [f for f in runnable if f.use_case == uc_filter]
        top = runnable[:args.limit]

        result = {
            "system": {
                "cpu": system.cpu_name,
                "ram_gb": round(system.available_ram_gb, 1),
                "gpu": system.gpu_name,
                "vram_gb": round(system.gpu_vram_gb, 1) if system.gpu_vram_gb else None,
                "backend": system.backend.value,
            },
            "models": [mf.to_dict() for mf in top],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # ── fit ────────────────────────────────────────────────────────────────
    if cmd == "fit":
        if args.perfect:
            fits = [f for f in fits if f.fit_level == FitLevel.PERFECT]
        else:
            fits = [f for f in fits if f.fit_level != FitLevel.TOO_TIGHT]

        if args.json:
            print(json.dumps([mf.to_dict() for mf in fits[:args.n or len(fits)]], indent=2, ensure_ascii=False))
        else:
            system.display()
            print_fits_table(fits, args.n)
        return

 # ── Default: only Perfect models ────────────────────────────────────────
    # Après
    perfect = [f for f in fits if f.fit_level != FitLevel.TOO_TIGHT and f.score > 85][:2]
    if args.json:
        print(json.dumps([mf.to_dict() for mf in perfect], indent=2, ensure_ascii=False))
    else:
        system.display()
        print_fits_table(perfect)


if __name__ == "__main__":
    main()

