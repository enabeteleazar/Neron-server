import asyncio
import json
import logging
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

WATCHED_CONTAINERS = {
    "neron_core":      "Neron Core",
    "neron_stt":       "Neron STT",
    "neron_memory":    "Neron Memory",
    "neron_tts":       "Neron TTS",
    "neron_llm":       "Neron LLM",
    "neron_ollama":    "Neron Ollama",
    "neron_searxng":   "Neron SearXNG",
    "neron_web_voice": "Neron Web Voice",
}

class DockerEventWatcher:
    """Surveille les evenements Docker via socket Unix"""

    def __init__(self, notifier, previous_states: dict):
        self.notifier = notifier
        self.previous_states = previous_states
        self.running = False

    async def watch(self):
        """Ecoute le stream Docker Events via socket Unix"""
        self.running = True
        logger.info("👁️ Docker Event Watcher démarré (via socket Unix)")

        while self.running:
            try:
                connector = aiohttp.UnixConnector(path="/var/run/docker.sock")
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(
                        "http://localhost/events",
                        params={
                            "filters": json.dumps({
                                "type": ["container"],
                                "event": ["die", "stop", "start", "restart"]
                            })
                        },
                        timeout=aiohttp.ClientTimeout(total=None)
                    ) as response:
                        async for line in response.content:
                            if not line.strip():
                                continue
                            try:
                                event = json.loads(line.decode().strip())
                                await self._handle_event(event)
                            except json.JSONDecodeError:
                                continue

            except Exception as e:
                logger.error(f"Erreur Docker Events: {e}")
                await asyncio.sleep(5)

    async def _handle_event(self, event: dict):
        """Traiter un evenement Docker"""
        container = event.get("Actor", {}).get("Attributes", {}).get("name", "")
        action = event.get("Action", "")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if container not in WATCHED_CONTAINERS:
            return

        service_name = WATCHED_CONTAINERS[container]
        logger.info(f"🐳 Event Docker: {action.upper()} -> {service_name}")

        if action == "die":  # stop + die sont emis ensemble, on garde seulement die
            self.previous_states[service_name] = False
            exit_code = event.get("Actor", {}).get("Attributes", {}).get("exitCode", "N/A")
            message = (
                f"🔴 <b>ALERTE - Service DOWN</b>\n\n"
                f"<b>Service:</b> {service_name}\n"
                f"<b>Événement:</b> {action.upper()}\n"
                f"<b>Exit code:</b> {exit_code}\n"
                f"<b>Détection:</b> Instantanée (Docker Events)\n"
                f"<b>Heure:</b> {timestamp}"
            )
            await self.notifier.send_alert(message)

        elif action in ("start", "restart"):
            was_healthy = self.previous_states.get(service_name, True)
            if not was_healthy:
                self.previous_states[service_name] = True
                message = (
                    f"🟢 <b>RÉCUPÉRATION - Service UP</b>\n\n"
                    f"<b>Service:</b> {service_name}\n"
                    f"<b>Événement:</b> {action.upper()}\n"
                    f"<b>Détection:</b> Instantanée (Docker Events)\n"
                    f"<b>Heure:</b> {timestamp}"
                )
                await self.notifier.send_success(message)

    def stop(self):
        self.running = False
