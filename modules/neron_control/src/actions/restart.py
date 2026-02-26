import asyncio
import aiohttp
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Mapping service -> nom conteneur Docker
SERVICE_TO_CONTAINER = {
    "Neron Core":      "neron_core",
    "Neron STT":       "neron_stt",
    "Neron Memory":    "neron_memory",
    "Neron TTS":       "neron_tts",
    "Neron LLM":       "neron_llm",
    "Neron Ollama":    "neron_ollama",
    "Neron SearXNG":   "neron_searxng",
    "Neron Web Voice": "neron_web_voice",
}

MAX_RETRIES = 3
RETRY_DELAYS = [10, 30, 60]  # secondes entre tentatives


class RestartAction:
    """Gere le restart automatique des services via Docker API"""

    def __init__(self, notifier, socket_path: str = "/var/run/docker.sock"):
        self.notifier = notifier
        self.socket_path = socket_path
        self.restart_counts = {}  # service -> nombre de restarts

    async def restart_service(self, service_name: str) -> bool:
        """Tenter de redemarrer un service"""
        container = SERVICE_TO_CONTAINER.get(service_name)
        if not container:
            logger.error(f"Conteneur inconnu pour le service: {service_name}")
            return False

        try:
            connector = aiohttp.UnixConnector(path=self.socket_path)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    f"http://localhost/containers/{container}/restart",
                    params={"t": 10}
                ) as response:
                    if response.status in (204, 200):
                        logger.info(f"✅ Restart {container} OK")
                        return True
                    else:
                        logger.error(f"❌ Restart {container} échoué: HTTP {response.status}")
                        return False

        except Exception as e:
            logger.error(f"❌ Erreur restart {container}: {e}")
            return False

    async def handle_down(self, service_name: str, checker=None) -> bool:
        """
        Pipeline complet de restart avec retry et notifications
        Retourne True si le service est revenu UP
        """
        count = self.restart_counts.get(service_name, 0)

        if count >= MAX_RETRIES:
            logger.error(f"🚨 {service_name} a dépassé {MAX_RETRIES} restarts - intervention manuelle requise")
            await self.notifier.send_alert(
                f"🚨 <b>INTERVENTION MANUELLE REQUISE</b>\n\n"
                f"<b>Service:</b> {service_name}\n"
                f"<b>Tentatives:</b> {count}/{MAX_RETRIES}\n"
                f"<b>Status:</b> Toujours DOWN après {MAX_RETRIES} restarts\n"
                f"<b>Heure:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return False

        delay = RETRY_DELAYS[count] if count < len(RETRY_DELAYS) else RETRY_DELAYS[-1]
        attempt = count + 1

        logger.warning(f"🔄 Tentative de restart {attempt}/{MAX_RETRIES} pour {service_name} (délai: {delay}s)")

        await self.notifier.send_warning(
            f"🔄 <b>Auto-restart en cours</b>\n\n"
            f"<b>Service:</b> {service_name}\n"
            f"<b>Tentative:</b> {attempt}/{MAX_RETRIES}\n"
            f"<b>Délai avant restart:</b> {delay}s\n"
            f"<b>Heure:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await asyncio.sleep(delay)

        success = await self.restart_service(service_name)
        self.restart_counts[service_name] = attempt

        if success:
            # Attendre que le service soit vraiment UP
            await asyncio.sleep(15)

            if checker:
                result = await checker.check()
                if result.is_healthy:
                    self.restart_counts[service_name] = 0  # Reset compteur
                    await self.notifier.send_success(
                        f"✅ <b>Service rétabli après restart</b>\n\n"
                        f"<b>Service:</b> {service_name}\n"
                        f"<b>Tentative:</b> {attempt}/{MAX_RETRIES}\n"
                        f"<b>Temps de réponse:</b> {result.response_time:.2f}s\n"
                        f"<b>Heure:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    return True
                else:
                    # Toujours DOWN -> nouvelle tentative récursive
                    return await self.handle_down(service_name, checker)
            return True

        return False

    def reset_counter(self, service_name: str):
        """Remettre le compteur de restart a zero quand le service revient UP"""
        if service_name in self.restart_counts:
            self.restart_counts[service_name] = 0
            logger.info(f"Compteur restart reset pour {service_name}")
