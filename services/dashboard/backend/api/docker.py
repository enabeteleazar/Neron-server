from fastapi import APIRouter
import docker
import time
from datetime import datetime, timezone

router = APIRouter()
client = docker.from_env()

def parse_docker_datetime(dt_str: str) -> str:
    if not dt_str:
        return None
        dt_str = dt_str.rstrip("Z")
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.isoformat() + "Z"
        except ValueError:
            return dt_str

@router.get("/docker")
def get_docker_overview():
    if not client:
        return {"error": "Docker client non disponible"}

    try:
        containers = client.containers.list(all=True)

        running = 0
        stopped = 0
        paused = 0
        container_list = []

        for c in containers:
            state = c.status

            if state == "running":
                running += 1
            elif state == "paused":
                paused += 1
            else:
                stopped += 1

            attrs = c.attrs
            created = parse_docker_datetime(attrs.get("Created"))
            started = parse_docker_datetime(attrs.get("State", {}).get("startedAt"))
            finished = parse_docker_datetime(attrs.get("State", {}).get("FinishedAt")) 

            container_list.append({
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else "unknown",
                "status": c.status,
                "created": created,
                "started": started,
                "finished": finished
            })

        return {
            "status": "ok",
            "summary": {
                "total": len(containers),
                "running": running,
                "stopped": stopped,
                "paused": paused
            },
            "containers": container_list,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
