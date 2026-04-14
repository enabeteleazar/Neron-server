"""Ollama provider — async HTTP via httpx.AsyncClient.

Config (neron.yaml → llm section):
    host: http://localhost:11434
    timeout: 300
"""

from __future__ import annotations

import logging

import httpx

from neron_llm.config import get_llm_config
from neron_llm.providers.base import BaseProvider

logger = logging.getLogger("neron_llm.ollama")


class OllamaProvider(BaseProvider):
    """Async provider for local Ollama instances."""

    def __init__(self):
        cfg = get_llm_config()
        self.host: str = cfg.get("host", "http://localhost:11434").rstrip("/")
        self.timeout: float = float(cfg.get("timeout", 300))

    async def generate(self, message: str, model: str) -> str:
        """Generate a response via Ollama's /api/generate endpoint.

        Raises:
            httpx.TimeoutException: On timeout.
            httpx.HTTPStatusError: On HTTP 4xx/5xx.
            ValueError: On unexpected response format.
            Exception: On any other failure.
        """
        url = f"{self.host}/api/generate"
        payload = {
            "model": model,
            "prompt": message,
            "stream": False,
        }

        logger.debug("ollama | POST %s model=%s", url, model)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

        if "response" not in data:
            raise ValueError(f"Ollama unexpected format: {list(data.keys())}")

        return data["response"]