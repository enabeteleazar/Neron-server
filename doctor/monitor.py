# app/monitor.py
# Surveillance système : CPU, RAM, disque, processus, services systemd

import subprocess
import time
from typing import Any
import psutil
from doctor.config import cfg
from doctor.logger import get_logger

log = get_logger("doctor.monitor")


# ─────────────────────────────────────────────
#  Métriques système
# ─────────────────────────────────────────────

def get_system_metrics() -> dict[str, Any]:
    log.debug("Collecting system metrics")

    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    metrics = {
        "cpu": {
            "percent": cpu,
            "count": psutil.cpu_count(),
            "status": "warn" if cpu >= cfg.CPU_WARN_PERCENT else "ok",
        },
        "memory": {
            "percent": mem.percent,
            "used_mb": round(mem.used / 1024 / 1024),
            "total_mb": round(mem.total / 1024 / 1024),
            "available_mb": round(mem.available / 1024 / 1024),
            "status": "warn" if mem.percent >= cfg.MEM_WARN_PERCENT else "ok",
        },
        "disk": {
            "percent": disk.percent,
            "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
            "status": "warn" if disk.percent >= cfg.DISK_WARN_PERCENT else "ok",
        },
    }

    # Alerte globale si un des systèmes est en warn
    metrics["global_status"] = (
        "warn"
        if any(v.get("status") == "warn" for v in metrics.values() if isinstance(v, dict))
        else "ok"
    )

    return metrics


# ─────────────────────────────────────────────
#  État des services systemd
# ─────────────────────────────────────────────

def get_service_status(service: str) -> dict[str, Any]:
    """Interroge systemctl pour un service donné."""
    try:
        out = subprocess.check_output(
            ["systemctl", "is-active", service],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        active = out == "active"
    except subprocess.CalledProcessError as e:
        out = e.output.strip() if e.output else "inactive"
        active = False
    except FileNotFoundError:
        out = "systemctl_not_found"
        active = False

    # Récupère le PID si actif
    pid = None
    if active:
        try:
            show = subprocess.check_output(
                ["systemctl", "show", service, "--property=MainPID"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
            pid_str = show.replace("MainPID=", "").strip()
            pid = int(pid_str) if pid_str.isdigit() else None
        except Exception:
            pass

    return {
        "service": service,
        "state": out,
        "active": active,
        "pid": pid,
        "status": "ok" if active else "error",
    }


def get_all_services_status() -> dict[str, Any]:
    log.info(f"Checking {len(cfg.SYSTEMD_SERVICES)} systemd services")
    results = {}
    for svc in cfg.SYSTEMD_SERVICES:
        results[svc] = get_service_status(svc)
    return results


# ─────────────────────────────────────────────
#  Analyse des logs journalctl
# ─────────────────────────────────────────────

ERROR_KEYWORDS = ("error", "exception", "traceback", "critical", "fatal", "failed")
WARN_KEYWORDS  = ("warning", "warn", "deprecated")


def get_journal_errors(service: str, lines: int = None) -> dict[str, Any]:
    """Récupère et analyse les derniers logs d'un service systemd."""
    n = lines or cfg.JOURNAL_LINES
    log.debug(f"Reading {n} journal lines for {service}")

    try:
        raw = subprocess.check_output(
            ["journalctl", "-u", service, "-n", str(n), "--no-pager", "--output=short"],
            text=True, stderr=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return {"service": service, "available": False, "error": str(e)}

    error_lines = []
    warn_lines  = []

    for line in raw.splitlines():
        lower = line.lower()
        if any(kw in lower for kw in ERROR_KEYWORDS):
            error_lines.append(line.strip())
        elif any(kw in lower for kw in WARN_KEYWORDS):
            warn_lines.append(line.strip())

    return {
        "service": service,
        "available": True,
        "lines_analyzed": len(raw.splitlines()),
        "errors": error_lines[-20:],    # 20 dernières erreurs max
        "warnings": warn_lines[-10:],
        "error_count": len(error_lines),
        "warn_count": len(warn_lines),
        "status": "error" if error_lines else ("warn" if warn_lines else "ok"),
    }


def get_all_journal_errors() -> dict[str, Any]:
    results = {}
    for svc in cfg.SYSTEMD_SERVICES:
        results[svc] = get_journal_errors(svc)
    return results
