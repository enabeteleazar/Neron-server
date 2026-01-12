#api/health.py
from fastapi import APIRouter
from datetime import datetime
import docker
import psutil
import socket
import requests
import time

router = APIRouter(prefix="/health", tags=["health"])
client = docker.from_env()

BOOT_TIME = psutil.boot_time()

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

# -----------------------------
# CHECKS BAS NIVEAU
# -----------------------------

def check_service_socket(host: str, port: int, timeout: int = 2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def check_service_http(url: str, timeout: int = 2) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False

# -----------------------------
# SYSTEM HEALTH
# -----------------------------

def system_health():
    try:
        cpu = psutil.cpu_percent(interval=0.3)
        ram = psutil.virtual_memory()

        return {
            "uptime_seconds": int(time.time() - BOOT_TIME),
            "cpu_percent": round(cpu, 1),
            "memory_percent": round(ram.percent, 1),
            "cpu_ok": cpu < 95,
            "memory_ok": ram.percent < 95
        }
    except Exception:
        return {
            "uptime_seconds": 0,
            "cpu_ok": False,
            "memory_ok": False
        }

# -----------------------------
# DOCKER HEALTH
# -----------------------------

def docker_health():
    try:
        client.ping()
        containers = client.containers.list(all=True)

        running = [c.name for c in containers if c.status == "running"]
        stopped = [c.name for c in containers if c.status != "running"]

        return {
            "available": True,
            "containers_total": len(containers),
            "containers_running": len(running),
            "containers_stopped": len(stopped),
            "stopped_list": stopped
        }
    except Exception:
        return {
            "available": False,
            "containers_total": 0,
            "containers_running": 0,
            "containers_stopped": 0,
            "stopped_list": []
        }

# -----------------------------
# SERVICES HEALTH
# -----------------------------

def services_health():
    """
    Services connus (non critiques par défaut)
    Les rôles critiques viendront plus tard (v1.5+)
    """
    services = {
        "cups": check_service_socket("127.0.0.1", 631),
        "home_assistant": check_service_http("http://127.0.0.1:8123"),
        "neron_llm": check_service_http("http://127.0.0.1:5001"),
        "codi_tv": check_service_http("http://127.0.0.1:5002"),
    }

    return {
        "ok": [name for name, status in services.items() if status],
        "down": [name for name, status in services.items() if not status]
    }

# -----------------------------
# ENDPOINTS
# -----------------------------

@router.get("/")
def health_global():
    system = system_health()
    docker_status = docker_health()
    services = services_health()

    status = "ok"

    if not docker_status["available"]:
        status = "down"
    elif not system["cpu_ok"] or not system["memory_ok"]:
        status = "degraded"
    elif services["down"]:
        status = "degraded"

    return {
        "status": status,
        "timestamp": now_iso(),
        "system": system,
        "docker": docker_status,
        "services": services
    }

@router.get("/system")
def health_system():
    return {
        "timestamp": now_iso(),
        "system": system_health()
    }

@router.get("/services")
def health_services():
    return {
        "timestamp": now_iso(),
        "docker": docker_health(),
        "services": services_health()
    }
