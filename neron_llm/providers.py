"""Ollama provider — async HTTP via a shared httpx.AsyncClient.

A single AsyncClient is created at instantiation and reused across
all generate() calls.  This enables HTTP keep-alive and connection
pooling, which significantly reduces latency and resource usage under
load compared to opening a new connection per request.

Config (neron.yaml → llm section):
    host: http://localhost:11434
    timeout: 300
    ollama_max_connections: 50          # optional, default 50
    ollama_max_keepalive_connections: 10  # optional, default 10
"""

from __future__ import annotations

import logging

import httpx

from neron_llm.config import get_llm_config
from neron_llm.providers.base import BaseProvider

logger = logging.getLogger("neron_llm.ollama")


class OllamaProvider(BaseProvider):
    """Async provider for local Ollama instances.

    The underlying httpx.AsyncClient is shared for the lifetime of this
    object.  Call aclose() (or use LLMManager.aclose()) to release the
    connection pool gracefully on shutdown.
    """

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
        """Generate a response via Ollama's /api/generate endpoint.

        Raises:
            httpx.TimeoutException: On timeout.
            httpx.HTTPStatusError: On HTTP 4xx/5xx.
            ValueError: On unexpected response format.
        """
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
        """Close the shared HTTP client and release connections."""
        await self._client.aclose()
        logger.debug("OllamaProvider: HTTP client closed")
