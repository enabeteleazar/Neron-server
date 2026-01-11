from fastapi import APIRouter
import docker
import psutil
import socket
import requests
import time
from utils.response import success_response, degraded_response, error_response

router = APIRouter(prefix=”/health”, tags=[“health”])

try:
client = docker.from_env()
except Exception:
client = None

BOOT_TIME = psutil.boot_time()

def check_service_socket(host: str, port: int, timeout: int = 2) -> bool:
“”“Vérifie si un service répond sur un port TCP”””
try:
with socket.create_connection((host, port), timeout=timeout):
return True
except Exception:
return False

def check_service_http(url: str, timeout: int = 2) -> bool:
“”“Vérifie si un service HTTP/HTTPS répond”””
try:
r = requests.get(url, timeout=timeout)
return r.status_code < 500
except Exception:
return False

def system_health():
“”“Santé du système (CPU, RAM, uptime)”””
try:
cpu = psutil.cpu_percent(interval=0.3)
ram = psutil.virtual_memory()
disk = psutil.disk_usage(”/”)

```
    return {
        "uptime_seconds": int(time.time() - BOOT_TIME),
        "cpu_percent": round(cpu, 1),
        "memory_percent": round(ram.percent, 1),
        "disk_percent": round(disk.percent, 1),
        "cpu_ok": cpu < 90,
        "memory_ok": ram.percent < 90,
        "disk_ok": disk.percent < 90
    }
except Exception as e:
    return {
        "uptime_seconds": 0,
        "cpu_ok": False,
        "memory_ok": False,
        "disk_ok": False,
        "error": str(e)
    }
```

def docker_health():
“”“Santé de Docker”””
try:
if not client:
return {
“available”: False,
“containers_total”: 0,
“containers_running”: 0,
“containers_stopped”: 0,
“stopped_list”: []
}

```
    client.ping()
    containers = client.containers.list(all=True)

    running = [c.name for c in containers if c.status == "running"]
    stopped = [c.name for c in containers if c.status != "running"]

    return {
        "available": True,
        "containers_total": len(containers),
        "containers_running": len(running),
        "containers_stopped": len(stopped),
        "running_list": running,
        "stopped_list": stopped
    }
except Exception as e:
    return {
        "available": False,
        "containers_total": 0,
        "containers_running": 0,
        "containers_stopped": 0,
        "stopped_list": [],
        "error": str(e)
    }
```

def services_health():
“””
Santé des services externes
À personnaliser selon tes services
“””
services = {
“cups”: check_service_socket(“127.0.0.1”, 631),
“home_assistant”: check_service_http(“http://127.0.0.1:8123”),
“neron_llm”: check_service_http(“http://127.0.0.1:5001”),
“codi_tv”: check_service_http(“http://127.0.0.1:5002”),
}

```
return {
    "ok": [name for name, status in services.items() if status],
    "down": [name for name, status in services.items() if not status],
    "total": len(services),
    "healthy_count": sum(1 for s in services.values() if s)
}
```

@router.get(”/”)
def health_global():
“””
Health check complet : système + docker + services
“””
system = system_health()
docker_status = docker_health()
services = services_health()

```
# Déterminer le status global
status = "ok"

if not docker_status["available"]:
    status = "degraded"
elif not system["cpu_ok"] or not system["memory_ok"] or not system["disk_ok"]:
    status = "degraded"
elif len(services["down"]) > 0:
    status = "degraded"

data = {
    "system": system,
    "docker": docker_status,
    "services": services
}

if status == "degraded":
    return degraded_response(data)

return success_response(data)
```

@router.get(”/system”)
def health_system():
“”“Health check système uniquement”””
system = system_health()

```
if not system["cpu_ok"] or not system["memory_ok"] or not system["disk_ok"]:
    return degraded_response({"system": system})

return success_response({"system": system})
```

@router.get(”/docker”)
def health_docker_only():
“”“Health check Docker uniquement”””
docker_status = docker_health()

```
if not docker_status["available"]:
    return degraded_response({"docker": docker_status})

return success_response({"docker": docker_status})
```

@router.get(”/services”)
def health_services():
“”“Health check services externes uniquement”””
docker_status = docker_health()
services = services_health()

```
data = {
    "docker": docker_status,
    "services": services
}

if not docker_status["available"] or len(services["down"]) > 0:
    return degraded_response(data)

return success_response(data)
```

@router.get(”/ping”)
def health_ping():
“”“Simple ping pour vérifier que l’API répond”””
return success_response({“message”: “pong”})
