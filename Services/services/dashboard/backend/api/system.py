from fastapi import APIRouter
import psutil
import time
from datetime import datetime

router = APIRouter(prefix="/system", tags=["system"])

BOOT_TIME = psutil.boot_time()


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


def get_temperature():
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None

        for entries in temps.values():
            if entries and entries[0].current is not None:
                return round(float(entries[0].current), 1)
    except Exception:
        pass

    return None


@router.get("/")
def get_system():
    cpu_percent = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")

    status = "ok"
    if cpu_percent >= 95 or ram.percent >= 95:
        status = "degraded"

    return {
        "status": status,
        "timestamp": now_iso(),
        "data": {
            "cpu": {
                "percent": round(cpu_percent, 1),
                "temperature": get_temperature()
            },
            "memory": {
                "ram": {
                    "percent": round(ram.percent, 1),
                    "used_mb": round(ram.used / 1024 / 1024),
                    "total_mb": round(ram.total / 1024 / 1024)
                },
                "swap": {
                    "percent": round(swap.percent, 1),
                    "used_mb": round(swap.used / 1024 / 1024),
                    "total_mb": round(swap.total / 1024 / 1024)
                }
            },
            "disk": {
                "percent": round(disk.percent, 1),
                "used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 1)
            },
            "uptime_seconds": int(time.time() - BOOT_TIME),
            "process_count": len(psutil.pids())
        }
    }
