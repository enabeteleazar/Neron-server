# providers/ollama.py
# Ollama provider — async HTTP via a shared httpx.AsyncClient.

from __future__ import annotations

import logging

import httpx

from neron_llm.config import get_llm_config
from neron_llm.providers.base import BaseProvider

logger = logging.getLogger("neron_llm.ollama")


class OllamaProvider(BaseProvider):

    def __init__(self) -> None:
        cfg = get_llm_config()
        host    = cfg.get("host", "http://localhost:11434").rstrip("/")
        timeout = float(cfg.get("timeout", 300))
        limits  = httpx.Limits(
            max_connections          = int(cfg.get("ollama_max_connections", 50)),
            max_keepalive_connections= int(cfg.get("ollama_max_keepalive_connections", 10)),
        )
        self._client = httpx.AsyncClient(
            base_url = host,
            timeout  = timeout,
            limits   = limits,
        )
        logger.debug("OllamaProvider initialised — base_url=%s timeout=%s", host, timeout)

    async def generate(self, message: str, model: str) -> str:
        payload = {
            "model":  model,
            "prompt": message,
            "stream": False,
        }

        logger.debug("ollama | POST /api/generate model=%s", model)

        r = await self._client.post("/api/generate", json=payload)
        r.raise_for_status()
        data = r.json()

        if "response" not in data:
            raise ValueError(f"Ollama unexpected format: {list(data.keys())}")

        return data["response"]

    async def aclose(self) -> None:
        await self._client.aclose()
        logger.debug("OllamaProvider: HTTP client closed")
