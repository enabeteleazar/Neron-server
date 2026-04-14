import logging

import httpx

from neron_llm.config import get_llm_config
from neron_llm.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """Appel async vers l'API Ollama locale.

    Utilise httpx.AsyncClient pour ne PAS bloquer l'event loop,
    ce qui est indispensable pour les modes parallel et race.

    Config neron.yaml :
        llm:
          host: http://localhost:11434
          timeout: 120
    """

    def __init__(self):
        cfg = get_llm_config()
        self.host: str = cfg.get("host", "http://localhost:11434").rstrip("/")
        self.timeout: float = float(cfg.get("timeout", 120))

    async def generate(self, message: str, model: str) -> str:
        url = f"{self.host}/api/generate"
        payload = {
            "model": model,
            "prompt": message,
            "stream": False,
        }

        logger.debug("ollama | POST %s model=%s", url, model)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
                return data.get("response", "")

        except httpx.TimeoutException:
            msg = f"[OLLAMA TIMEOUT] Ollama n'a pas répondu en {self.timeout}s"
            logger.error(msg)
            return msg

        except httpx.HTTPStatusError as exc:
            msg = f"[OLLAMA HTTP {exc.response.status_code}] {exc.response.text[:200]}"
            logger.error(msg)
            return msg

        except Exception as exc:
            msg = f"[OLLAMA ERREUR] {exc}"
            logger.error(msg)
            return msg
