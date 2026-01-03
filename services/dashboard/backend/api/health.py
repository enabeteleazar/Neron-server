from fastapi import APIRouter
from datetime import datetime
import docker
import socket
import requests

router = APIRouter()
client = docker.from_env()


def check_service_socket(host: str, port: int, timeout: int = 2) -> str:
    """
    Vérifie si un service est joignable via TCP.
    Retourne "ok" si reachable, "error" sinon.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "ok"
    except Exception:
        return "error"


def check_service_http(url: str, timeout: int = 2) -> str:
    """
    Vérifie si un service HTTP est accessible.
    Retourne "ok" si reachable (status code 200), "error" sinon.
    """
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return "ok"
        else:
            return "error"
    except Exception:
        return "error"


@router.get("/health")
def health_check():
    """
    Endpoint de santé complet pour Homebox/Néron.
    Teste :
    - Docker
    - CUPS
    - Home Assistant
    - Néron LLM
    - Codi-TV
    Retourne un résumé par service et un état global.
    """
    try:
        # --- Docker ---
        docker_status = "ok"
        try:
            client.ping()
        except Exception:
            docker_status = "error"

        # --- CUPS ---
        cups_status = check_service_socket(host="127.0.0.1", port=631)

        # --- Home Assistant ---
        home_assistant_status = check_service_http("http://127.0.0.1:8123")

        # --- Néron LLM ---
        neron_llm_status = check_service_http("http://127.0.0.1:5001")  # à adapter si port différent

        # --- Codi-TV ---
        codi_tv_status = check_service_http("http://127.0.0.1:5002")  # à adapter selon port réel

        # Liste des statuts
        services = {
            "docker": docker_status,
            "cups": cups_status,
            "home_assistant": home_assistant_status,
            "neron_llm": neron_llm_status,
            "codi_tv": codi_tv_status
        }

        # État global : "ok" si tous les services sont "ok"
        global_status = "ok" if all(status == "ok" for status in services.values()) else "error"

        return {
            "status": global_status,
            "services": services,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
