import asyncio
import json
import logging
import aiohttp
import time
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

# Délai avant reprise après rebuild (secondes)
REBUILD_RESUME_DELAY = 60


class DockerEventWatcher:
    """Surveille les evenements Docker via socket Unix"""

    def __init__(self, notifier, previous_states: dict, restart_counts: dict = None, restart_action=None, service_checkers: dict = None, control_plane=None):
        self.notifier = notifier
        self.previous_states = previous_states
        self.restart_counts = restart_counts or {}
        self.restart_action = restart_action
        self.service_checkers = service_checkers or {}
        self.control_plane = control_plane
        self._start_time = time.time()
        self.running = False
        self._rebuild_timer = None
        self._paused_by_rebuild = False

    async def watch(self):
        """Ecoute le stream Docker Events via socket Unix"""
        self.running = True
        logger.info("👁️ Docker Event Watcher démarré (via socket Unix)")

        while self.running:
            try:
                connector = aiohttp.UnixConnector(path="/var/run/docker.sock")
                async with aiohttp.ClientSession(connector=connector) as session:
                    # Écouter containers ET images (pour détecter les builds)
                    async with session.get(
                        "http://localhost/events",
                        params={
                            "filters": json.dumps({
                                "type": ["container", "image"],
                                "event": ["die", "stop", "start", "restart", "build", "destroy"]
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
        # Ignorer les événements antérieurs au démarrage
        event_time = event.get("time", 0)
        if event_time and event_time < self._start_time:
            return

        event_type = event.get("Type", "container")
        action = event.get("Action", "")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ── Détection rebuild image ──────────────────────────────────
        if event_type == "image" and action == "build":
            await self._on_rebuild_detected(timestamp)
            return

        # ── Détection recreate conteneur (pendant docker compose up) ─
        container = event.get("Actor", {}).get("Attributes", {}).get("name", "")
        if action == "destroy" and container in WATCHED_CONTAINERS:
            await self._on_rebuild_detected(timestamp)
            return

        # ── Events conteneurs surveillés ─────────────────────────────
        if container not in WATCHED_CONTAINERS:
            return

        service_name = WATCHED_CONTAINERS[container]
        logger.info(f"🐳 Event Docker: {action.upper()} -> {service_name}")

        if action == "die":
            # Si pause rebuild active → ignorer les die (c'est le rebuild)
            if self._paused_by_rebuild:
                logger.info(f"⏸️ Rebuild en cours — die ignoré pour {service_name}")
                return

            self.previous_states[service_name] = False
            if self.restart_action and self.restart_counts.get(service_name, 0) == 0:
                checker = self.service_checkers.get(service_name)
                asyncio.create_task(
                    self.restart_action.handle_down(service_name, checker)
                )
            else:
                exit_code = event.get("Actor", {}).get("Attributes", {}).get("exitCode", "N/A")
                await self.notifier.send_alert(
                    f"🔴 <b>ALERTE - Service DOWN</b>\n\n"
                    f"<b>Service:</b> {service_name}\n"
                    f"<b>Exit code:</b> {exit_code}\n"
                    f"<b>Heure:</b> {timestamp}"
                )

        elif action in ("start", "restart"):
            self.previous_states[service_name] = True
            logger.info(f"🟢 {service_name} redémarré")

    async def _on_rebuild_detected(self, timestamp: str):
        """Pause automatique pendant un rebuild"""
        if self._paused_by_rebuild:
            # Rebuild toujours en cours → reset le timer
            if self._rebuild_timer:
                self._rebuild_timer.cancel()
            self._rebuild_timer = asyncio.create_task(self._auto_resume())
            return

        logger.info("🔨 Rebuild détecté — mise en pause du watchdog")
        self._paused_by_rebuild = True

        # Pause du control_plane
        if self.control_plane:
            self.control_plane.running = False
            await self.notifier.send_info(
                f"⏸️ <b>Watchdog en pause</b>\n"
                f"Rebuild détecté — reprise automatique dans {REBUILD_RESUME_DELAY}s\n"
                f"<i>{timestamp}</i>"
            )

        # Timer de reprise automatique
        if self._rebuild_timer:
            self._rebuild_timer.cancel()
        self._rebuild_timer = asyncio.create_task(self._auto_resume())

    async def _auto_resume(self):
        """Reprendre le watchdog après le délai"""
        await asyncio.sleep(REBUILD_RESUME_DELAY)

        if self._paused_by_rebuild and self.control_plane:
            self.control_plane.running = True
            self._paused_by_rebuild = False
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info("▶️ Watchdog repris automatiquement après rebuild")
            await self.notifier.send_info(
                f"▶️ <b>Watchdog repris</b>\n"
                f"Rebuild terminé — surveillance active\n"
                f"<i>{timestamp}</i>"
            )

    def stop(self):
        self.running = False
        if self._rebuild_timer:
            self._rebuild_timer.cancel()
