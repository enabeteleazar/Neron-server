import logging
import os

import httpx

from neron_llm.config import get_llm_config
from neron_llm.providers.base import BaseProvider

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class ClaudeProvider(BaseProvider):
    """Appel async vers l'API Anthropic Claude.

    La clé API est lue depuis la variable d'environnement ANTHROPIC_API_KEY
    ou depuis neron.yaml → llm.claude_api_key.

    Config neron.yaml (optionnel) :
        llm:
          claude_api_key: sk-ant-...
          claude_max_tokens: 1024
    """

    def __init__(self):
        cfg = get_llm_config()
        self.api_key: str = (
            os.getenv("ANTHROPIC_API_KEY")
            or cfg.get("claude_api_key", "")
        )
        self.max_tokens: int = int(cfg.get("claude_max_tokens", 1024))
        self.timeout: float = float(cfg.get("timeout", 120))

        if not self.api_key:
            logger.warning(
                "ClaudeProvider : ANTHROPIC_API_KEY absent — les appels échoueront."
            )

    async def generate(self, message: str, model: str) -> str:
        if not self.api_key:
            return "[CLAUDE] Clé API manquante (ANTHROPIC_API_KEY non définie)"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": message}],
        }

        logger.debug("claude | POST %s model=%s", ANTHROPIC_API_URL, model)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                # Anthropic retourne content[0].text pour les réponses texte
                return data["content"][0]["text"]

        except httpx.TimeoutException:
            msg = f"[CLAUDE TIMEOUT] Claude n'a pas répondu en {self.timeout}s"
            logger.error(msg)
            return msg

        except httpx.HTTPStatusError as exc:
            msg = f"[CLAUDE HTTP {exc.response.status_code}] {exc.response.text[:200]}"
            logger.error(msg)
            return msg

        except Exception as exc:
            msg = f"[CLAUDE ERREUR] {exc}"
            logger.error(msg)
            return msg
