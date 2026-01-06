from fastapi import APIRouter
import psutil
import time
from datetime import datetime

router = APIRouter(prefix="/system", tags=["system"])

BOOT_TIME = psutil.boot_time()


def get_temperature() -> float:
    """Retourne la température principale si disponible"""
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for entries in temps.values():
                if entries and entries[0].current is not None:
                    return round(float(entries[0].current), 1)
    except Exception:
        pass
    return 0.0


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


@router.get("/")
def get_system():
    """Retourne toutes les métriques système détaillées"""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")

    return {
        "status": "ok",
        "cpu": {
            "percent": round(cpu_percent, 1),
            "temperature": get_temperature()
        },
        "ram": {
            "used": round(ram.used / 1024 / 1024),
            "total": round(ram.total / 1024 / 1024),
            "percent": round(ram.percent, 1)
        },
        "swap": {
            "used": round(swap.used / 1024 / 1024),
            "total": round(swap.total / 1024 / 1024),
            "percent": round(swap.percent, 1)
        },
        "disk": {
            "used": round(disk.used / 1024 / 1024 / 1024, 1),
            "total": round(disk.total / 1024 / 1024 / 1024, 1),
            "percent": round(disk.percent, 1)
        },
        "uptime_seconds": int(time.time() - BOOT_TIME),
        "process_count": len(psutil.pids()),
        "timestamp": now_iso()
    }


@router.get("/summary")
def get_summary():
    """Résumé simplifié pour Dashboard : CPU %, RAM %, Disk %, Température"""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    ram_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage("/").percent
    temp = get_temperature()

    return {
        "timestamp": now_iso(),
        "summary": {
            "cpu_percent": round(cpu_percent, 1),
            "ram_percent": round(ram_percent, 1),
            "disk_percent": round(disk_percent, 1),
            "temperature": temp
        }
    }
