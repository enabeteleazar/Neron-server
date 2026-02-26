"""
Notifier Telegram - délègue à neron_telegram
"""

import logging
import httpx
import os

logger = logging.getLogger(__name__)

NERON_TELEGRAM_URL = os.getenv("NERON_TELEGRAM_URL", "http://neron_telegram:8010")


class TelegramNotifier:
    """Envoie les notifications via le service neron_telegram"""

    def __init__(self, token: str = None, chat_id: str = None):
        # token et chat_id conservés pour compatibilité mais non utilisés
        self.url = NERON_TELEGRAM_URL
        logger.info(f"TelegramNotifier → {self.url}")

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        return await self.send_info(text)

    async def send_alert(self, message: str) -> bool:
        return await self._notify("alert", message)

    async def send_warning(self, message: str) -> bool:
        return await self._notify("warning", message)

    async def send_recovery(self, message: str) -> bool:
        return await self._notify("info", message)

    async def send_info(self, message: str) -> bool:
        return await self._notify("info", message)

    async def _notify(self, level: str, message: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.url}/notify",
                    json={"level": level, "message": message},
                    timeout=10
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Erreur envoi notification: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.url}/health", timeout=5)
                return resp.status_code == 200
        except Exception:
            return False
