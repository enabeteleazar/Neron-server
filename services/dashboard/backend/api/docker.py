from fastapi import APIRouter
import docker
from datetime import datetime

router = APIRouter()
client = docker.from_env()

def format_datetime(dt_str):
    """Convertit une string ISO en datetime UTC"""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", ""))
    except Exception:
        return None

@router.get("/docker")
def get_containers():
    container_list = []

    try:
        containers = client.containers.list(all=True)
        for c in containers:
            created = format_datetime(c.attrs['Created'])
            started = format_datetime(c.attrs['State']['StartedAt'])
            finished = format_datetime(c.attrs['State'].get('FinishedAt', None))

            # Calcul uptime uniquement si le container est running
            uptime = str(datetime.utcnow() - started).split('.')[0] if c.status == "running" and started else "-"

            container_list.append({
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else "unknown",
                "status": c.status,
                "created": created,
                "started": started,
                "finished": finished,
                "port": next(iter(c.ports or {}), "-"),
                "uptime": uptime
            })

        summary = {
            "total": len(containers),
            "running": sum(1 for c in containers if c.status == "running"),
            "stopped": sum(1 for c in containers if c.status == "exited"),
            "paused": sum(1 for c in containers if c.status == "paused"),
        }

        return {"containers": container_list, "summary": summary}

    except Exception as e:
        return {"containers": [], "summary": {"total":0, "running":0, "stopped":0, "paused":0}, "error": str(e)}
