from fastapi import APIRouter
import docker
from datetime import datetime
import logging

router = APIRouter()
client = docker.from_env()

# Configuration logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docker-api")

def format_datetime(dt_str):
    """Convertit une string ISO en datetime UTC"""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", ""))
    except Exception:
        return None

def get_uptime(container):
    """Calcule l'uptime si container running"""
    started = format_datetime(container.attrs['State']['StartedAt'])
    if container.status == "running" and started:
        return str(datetime.utcnow() - started).split('.')[0]
    return "-"

def get_main_port(container):
    """Récupère le premier port exposé, ou '-' si aucun"""
    ports_dict = container.ports or {}
    if ports_dict:
        port_info = next(iter(ports_dict.values()))
        if port_info and isinstance(port_info, list):
            return port_info[0].get("HostPort", "-")
    return "-"

@router.get("/docker/list")
def docker_list():
    """Liste complète des containers Docker"""
    try:
        containers = client.containers.list(all=True)
        container_list = []
        for c in containers:
            container_list.append({
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else "unknown",
                "status": c.status,
                "created": format_datetime(c.attrs['Created']),
                "started": format_datetime(c.attrs['State']['StartedAt']),
                "finished": format_datetime(c.attrs['State'].get('FinishedAt', None)),
                "port": get_main_port(c),
                "uptime": get_uptime(c)
            })
            logger.info(f"Container {c.name} ({c.short_id}) processed.")

        return {"containers": container_list}

    except Exception as e:
        logger.error(f"Erreur docker_list: {str(e)}")
        return {"containers": [], "error": str(e)}

@router.get("/docker/summary")
def docker_summary():
    """Résumé rapide pour dashboard"""
    try:
        containers = client.containers.list(all=True)
        summary = {
            "total": len(containers),
            "running": sum(1 for c in containers if c.status == "running"),
            "stopped": sum(1 for c in containers if c.status == "exited"),
            "paused": sum(1 for c in containers if c.status == "paused"),
        }
        return {"summary": summary}

    except Exception as e:
        logger.error(f"Erreur docker_summary: {str(e)}")
        return {"summary": {"total": 0, "running": 0, "stopped": 0, "paused": 0}, "error": str(e)}

@router.post("/docker/{container_id}/stop")
def stop_container(container_id: str):
    """Arrête le container Docker si il est running"""
    try:
        c = client.containers.get(container_id)
        if c.status != "running":
            return {"detail": "Container déjà arrêté"}
        c.stop()
        logger.info(f"Container {container_id} stopped.")
        return {"status": "ok", "action": "stop", "container": container_id}
    except Exception as e:
        logger.error(f"Erreur stop_container({container_id}): {str(e)}")
        return {"error": str(e)}

@router.post("/docker/{container_id}/start")
def start_container(container_id: str):
    """Démarre le container Docker si il n'est pas running"""
    try:
        c = client.containers.get(container_id)
        if c.status == "running":
            return {"detail": "Container déjà démarré"}
        c.start()
        logger.info(f"Container {container_id} started.")
        return {"status": "ok", "action": "start", "container": container_id}
    except Exception as e:
        logger.error(f"Erreur start_container({container_id}): {str(e)}")
        return {"error": str(e)}
