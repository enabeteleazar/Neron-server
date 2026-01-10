from fastapi import APIRouter
from datetime import datetime
import docker
from datetime import datetime

router = APIRouter(prefix="/docker", tags=["docker"])
client = docker.from_env()


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


def format_datetime(dt_str):
    """Convertit une string ISO en datetime UTC"""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", ""))
    except Exception:
        return None


def get_containers_list():
    container_list = []
    try:
        containers = client.containers.list(all=True)
        for c in containers:
            created = format_datetime(c.attrs['Created'])
            started = format_datetime(c.attrs['State']['StartedAt'])
            finished = format_datetime(c.attrs['State'].get('FinishedAt', None))

            uptime = str(datetime.utcnow() - started).split('.')[0] if c.status == "running" and started else "-"

            ports_dict = c.ports or {}
            port = "-"
            if ports_dict:
                port_info = next(iter(ports_dict.values()))
                if port_info and isinstance(port_info, list):
                    port = port_info[0].get("HostPort", "-")

            container_list.append({
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else "unknown",
                "status": c.status,
                "created": created,
                "started": started,
                "finished": finished,
                "port": port,
                "uptime": uptime
            })

        return container_list
    except Exception:
        return []


def get_docker_summary(containers):
    total = len(containers)
    running = sum(1 for c in containers if c["status"] == "running")
    stopped = sum(1 for c in containers if c["status"] in ["exited", "created"])
    paused = sum(1 for c in containers if c["status"] == "paused")

    return {
        "total": total,
        "running": running,
        "stopped": stopped,
        "paused": paused
    }


def docker_status_global(summary):
    if summary["total"] == 0:
        return "down"
    elif summary["running"] == 0:
        return "degraded"
    else:
        return "ok"


@router.get("/list")
def docker_list():
    containers = get_containers_list()
    summary = get_docker_summary(containers)
    status = docker_status_global(summary)

    return {
        "status": status,
        "timestamp": now_iso(),
        "data": {
            "containers": containers,
            "summary": summary
        }
    }


@router.get("/summary")
def docker_summary():
    containers = get_containers_list()
    summary = get_docker_summary(containers)
    status = docker_status_global(summary)

    return {
        "status": status,
        "timestamp": now_iso(),
        "data": {
            "summary": summary
        }
    }


@router.post("/{container_id}/stop")
def stop_container(container_id: str):
    try:
        c = client.containers.get(container_id)
        if c.status != "running":
            return {
                "status": "degraded",
                "timestamp": now_iso(),
                "data": {"detail": "Container déjà arrêté"}
            }
        c.stop()
        return {
            "status": "ok",
            "timestamp": now_iso(),
            "data": {"action": "stop", "container": container_id}
        }
    except Exception as e:
        return {
            "status": "down",
            "timestamp": now_iso(),
            "data": {"error": str(e)}
        }


@router.post("/{container_id}/start")
def start_container(container_id: str):
    try:
        c = client.containers.get(container_id)
        if c.status == "running":
            return {
                "status": "degraded",
                "timestamp": now_iso(),
                "data": {"detail": "Container déjà démarré"}
            }
        c.start()
        return {
            "status": "ok",
            "timestamp": now_iso(),
            "data": {"action": "start", "container": container_id}
        }
    except Exception as e:
        return {
            "status": "down",
            "timestamp": now_iso(),
            "data": {"error": str(e)}
        }
