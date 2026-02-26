import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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
RETRY_DELAYS = [10, 30, 60]

# Seuils instabilité
INSTABILITY_THRESHOLD = 3   # crashs
INSTABILITY_WINDOW = 10     # minutes


class RestartAction:
    """Gere le restart automatique des services via Docker API"""

    def __init__(self, notifier, socket_path: str = "/var/run/docker.sock"):
        self.notifier = notifier
        self.socket_path = socket_path
        self.restart_counts = {}   # service -> tentatives restart en cours
        self.crash_history = {}    # service -> liste de timestamps des crashs
        self._locks = {}           # service -> asyncio.Lock (anti doublon)

    def _record_crash(self, service_name: str) -> int:
        """Enregistrer un crash et retourner le nombre de crashs recents"""
        now = datetime.now()
        window = now - timedelta(minutes=INSTABILITY_WINDOW)

        if service_name not in self.crash_history:
            self.crash_history[service_name] = []

        # Ajouter le crash actuel
        self.crash_history[service_name].append(now)

        # Nettoyer les crashs hors fenetre
        self.crash_history[service_name] = [
            t for t in self.crash_history[service_name] if t > window
        ]

        count = len(self.crash_history[service_name])
        logger.info(f"📊 {service_name}: {count} crash(s) dans les {INSTABILITY_WINDOW} dernières minutes")
        return count

    async def restart_service(self, service_name: str) -> bool:
        """Tenter de redemarrer un service via Docker API"""
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

    async def handle_down(self, service_name: str, checker=None):
        """
        Pipeline de restart silencieux.
        Alerte uniquement si service instable (3 crashs en 10min)
        ou intervention manuelle requise (3 restarts échoués).
        """
        # Verrou anti-doublon par service
        if service_name not in self._locks:
            self._locks[service_name] = asyncio.Lock()
        
        if self._locks[service_name].locked():
            logger.debug(f"⏭️ Restart déjà en cours pour {service_name}, ignoré")
            # Enregistrer quand même le crash pour comptage instabilité
            self._record_crash(service_name)
            return
        
        async with self._locks[service_name]:
            await self._do_restart(service_name, checker)

    async def _do_restart(self, service_name: str, checker=None):
        """Pipeline restart protégé par verrou"""
        # Enregistrer le crash
        crash_count = self._record_crash(service_name)

        # Alerte instabilité si seuil atteint
        if crash_count >= INSTABILITY_THRESHOLD:
            logger.warning(f"🔴 {service_name} instable: {crash_count} crashs en {INSTABILITY_WINDOW}min")
            await self.notifier.send_alert(
                f"🔴 <b>Service instable</b>\n\n"
                f"<b>Service:</b> {service_name}\n"
                f"<b>Crashs:</b> {crash_count} en {INSTABILITY_WINDOW} minutes\n"
                f"<b>Heure:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # Pipeline restart silencieux
        attempt = 0
        while attempt < MAX_RETRIES:
            attempt += 1
            delay = RETRY_DELAYS[attempt - 1]

            logger.warning(f"🔄 Restart {attempt}/{MAX_RETRIES} pour {service_name} (délai: {delay}s)")
            self.restart_counts[service_name] = attempt

            await asyncio.sleep(delay)

            success = await self.restart_service(service_name)
            if not success:
                continue

            # Attendre démarrage
            await asyncio.sleep(15)

            if checker:
                result = await checker.check()
                if result.is_healthy:
                    logger.info(f"✅ {service_name} rétabli après restart {attempt}/{MAX_RETRIES}")
                    self.restart_counts[service_name] = 0
                    return
            else:
                self.restart_counts[service_name] = 0
                return

        # 3 restarts échoués -> intervention manuelle
        logger.error(f"🚨 {service_name} - intervention manuelle requise")
        self.restart_counts[service_name] = 0
        await self.notifier.send_alert(
            f"🚨 <b>INTERVENTION MANUELLE REQUISE</b>\n\n"
            f"<b>Service:</b> {service_name}\n"
            f"<b>Tentatives:</b> {MAX_RETRIES}/{MAX_RETRIES} échouées\n"
            f"<b>Heure:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def reset_counter(self, service_name: str):
        """Remettre le compteur de restart a zero"""
        if service_name in self.restart_counts:
            self.restart_counts[service_name] = 0
