# app/config.py
# Configuration chargée depuis /etc/neron/neron.yaml (section "doctor:")
# Fallback sur des valeurs par défaut si la clé est absente.

import os
import yaml
from typing import Any

YAML_PATH = os.getenv("NERON_CONFIG", "/etc/neron/neron.yaml")


def _load_yaml(path: str) -> dict[str, Any]:
    """Charge le fichier YAML global Néron et retourne la section 'doctor'."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Neron config not found: {path}\n"
            f"Hint: copie neron.yaml.example vers {path} et adapte-le."
        )
    with open(path, encoding="utf-8") as f:
        full = yaml.safe_load(f) or {}
    return full.get("doctor", {})


def _get(d: dict, key: str, default: Any) -> Any:
    """Lecture avec fallback typé."""
    val = d.get(key, default)
    if val is None:
        return default
    if isinstance(default, bool):
        return bool(val)
    if isinstance(default, float):
        return float(val)
    if isinstance(default, int):
        return int(val)
    return val


class Config:
    def __init__(self, yaml_path: str = YAML_PATH):
        d = _load_yaml(yaml_path)

        # ── Chemins ──────────────────────────────────────────
        paths = d.get("paths", {})
        self.SERVER_PATH: str = paths.get("server", "/etc/neron/server")
        self.LLM_PATH:    str = paths.get("llm",    "/etc/neron/llm")
        self.LOG_DIR:     str = paths.get("logs",   "/var/log/neron")

        # ── Endpoints HTTP ───────────────────────────────────
        endpoints = d.get("endpoints", {})
        self.SERVER_HEALTH_URL: str = endpoints.get("server_health", "http://localhost:8010/health")
        self.SERVER_STATUS_URL: str = endpoints.get("server_status", "http://localhost:8010/status")
        self.LLM_HEALTH_URL:    str = endpoints.get("llm_health",    "http://localhost:8765/llm/health")
        self.OLLAMA_URL:        str = endpoints.get("ollama",         "http://localhost:11434/api/tags")

        # ── Services systemd ──────────────────────────────────
        self.SYSTEMD_SERVICES: list[str] = d.get(
            "services", ["neron-server", "neron-llm", "ollama"]
        )

        # ── Auth ─────────────────────────────────────────────
        self.API_KEY: str = d.get("api_key", "")

        # ── Timeouts & retry ──────────────────────────────────
        timing = d.get("timing", {})
        self.HTTP_TIMEOUT:    int = _get(timing, "http_timeout",    5)
        self.FIX_RETRY_COUNT: int = _get(timing, "fix_retry_count", 3)
        self.FIX_RETRY_DELAY: int = _get(timing, "fix_retry_delay", 4)
        self.JOURNAL_LINES:   int = _get(timing, "journal_lines",   100)

        # ── Seuils d'alerte système ───────────────────────────
        thresholds = d.get("thresholds", {})
        self.CPU_WARN_PERCENT:  float = _get(thresholds, "cpu",  80.0)
        self.MEM_WARN_PERCENT:  float = _get(thresholds, "mem",  85.0)
        self.DISK_WARN_PERCENT: float = _get(thresholds, "disk", 90.0)


cfg = Config()
