# agents/system_agent.py
# Supervision du système
# Agent SYSTEM_STATUS - interroge neron_watchdog

import httpx
import logging
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)

WATCHDOG_URL = settings.NERON_WATCHDOG_URL


async def handle_system_status(query: str) -> str:
    """
    Interroge le watchdog NERON et retourne un résumé de l'état système.

    Args:
        query: Requête utilisateur à analyser.

    Returns:
        Chaîne décrivant l'état du système ou un message d'erreur.
    """
    q = query.lower()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if any(word in q for word in ["cpu", "ram", "memoire", "ressource"]):
                return await _get_resources_status(client)
            return await _get_services_status(client)
    except httpx.TimeoutException:
        logger.error("Timeout lors de la connexion au watchdog")
        return "Impossible de contacter le watchdog (timeout)."
    except httpx.RequestError as e:
        logger.error(f"Erreur de connexion au watchdog: {e}")
        return "Impossible de contacter le watchdog."


async def _get_resources_status(client: httpx.AsyncClient) -> str:
    """Récupère et formate les statistiques de ressources."""
    response = await client.get(f"{WATCHDOG_URL}/docker-stats")
    response.raise_for_status()
    data = response.json()
    stats = data.get("stats", {})

    total_cpu = sum(s.get("cpu", 0) for s in stats.values())
    total_ram = sum(s.get("ram_mb", 0) for s in stats.values())
    top = sorted(
        stats.items(),
        key=lambda x: x[1].get("cpu", 0),
        reverse=True
    )[:3]
    top_str = ", ".join(
        f"{name} ({s.get('cpu', 0):.1f}%)" for name, s in top
    )
    return f"CPU total {total_cpu:.1f}%, RAM {total_ram:.0f}MB. Plus actifs : {top_str}."


async def _get_services_status(client: httpx.AsyncClient) -> str:
    """Récupère et formate l'état des services."""
    response = await client.get(f"{WATCHDOG_URL}/status")
    response.raise_for_status()
    data = response.json()
    services = data.get("services", {})
    total = len(services)
    healthy = sum(1 for s in services.values() if s.get("healthy"))
    down = [name for name, s in services.items() if not s.get("healthy")]
    score = (healthy / total * 100) if total else 0

    if down:
        return f"Score {score:.0f}%. Probleme sur : {', '.join(down)}."
    return f"Systeme nominal. {total} services actifs, score {score:.0f}%."
