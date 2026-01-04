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
    """
    Retourne la liste des containers Docker avec :
    - id, name, image, status
    - ports exposés
    - uptime si container running, sinon "-"
    - résumé total/running/stopped/paused
    """
    container_list = []
    try:
        containers = client.containers.list(all=True)
        for c in containers:
            created = format_datetime(c.attrs['Created'])
            started = format_datetime(c.attrs['State']['StartedAt'])
            finished = format_datetime(c.attrs['State'].get('FinishedAt', None))

            # Calcul uptime uniquement si le container est running
            uptime = str(datetime.utcnow() - started).split('.')[0] if c.status == "running" and started else "-"

            # Récupération du port exposé principal (s’il existe)
            ports_dict = c.ports or {}
            port = "-"
            if ports_dict:
                # Prend le premier port exposé et la première IP
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

        summary = {
            "total": len(containers),
            "running": sum(1 for c in containers if c.status == "running"),
            "stopped": sum(1 for c in containers if c.status == "exited"),
            "paused": sum(1 for c in containers if c.status == "paused"),
        }

        return {"containers": container_list, "summary": summary}

    except Exception as e:
        return {
            "containers": [],
            "summary": {"total": 0, "running": 0, "stopped": 0, "paused": 0},
            "error": str(e)
        }


@router.post("/docker/{container_id}/stop")
def stop_container(container_id: str):
    """Arrête le container Docker si il est running"""
    c = client.containers.get(container_id)
    if c.status != "running":
        return {"detail": "Container déjà arrêté"}
    c.stop()
    return {"status": "ok", "action": "stop", "container": container_id}


@router.post("/docker/{container_id}/start")
def start_container(container_id: str):
    """Démarre le container Docker si il n'est pas running"""
    c = client.containers.get(container_id)
    if c.status == "running":
        return {"detail": "Container déjà démarré"}
    c.start()
    return {"status": "ok", "action": "start", "container": container_id}
