# providers/claude.py
# Claude (Anthropic) provider — async HTTP via a shared httpx.AsyncClient.

from __future__ import annotations

import logging
import os

import httpx

from neron_llm.config import get_llm_config
from neron_llm.providers.base import BaseProvider

logger = logging.getLogger("neron_llm.claude")

ANTHROPIC_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_VERSION  = "2023-06-01"


class ClaudeProvider(BaseProvider):

    def __init__(self) -> None:
        cfg = get_llm_config()

        self.api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            logger.warning(
                "ClaudeProvider:ANTHROPIC_API_KEY not set - call will raise."
            )

        self.max_tokens:  int   = int(cfg.get("claude_max_tokens", 1024))
        self.temperature: float = float(cfg.get("temperature", 0.7))
        timeout = float(cfg.get("timeout", 300))
        limits  = httpx.Limits(
            max_connections          = int(cfg.get("claude_max_connections", 20)),
            max_keepalive_connections= int(cfg.get("claude_max_keepalive_connections", 5)),
        )

        # Authentication headers are baked into the client once at startup.
        # No need to rebuild them on every generate() call.
        self._client = httpx.AsyncClient(
            base_url = ANTHROPIC_BASE_URL,
            timeout  = timeout,
            limits   = limits,
            headers  = {
                "x-api-key":          self.api_key,
                "anthropic-version":  ANTHROPIC_VERSION,
                "content-type":       "application/json",
            },
        )
        logger.debug("ClaudeProvider initialised — timeout=%s max_tokens=%s", timeout, self.max_tokens)

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, message: str, model: str) -> str:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        payload = {
            "model":      model,
            "max_tokens": self.max_tokens,
            "temperature":self.temperature,
            "messages":   [{"role": "user", "content": message}],
        }

        logger.debug("claude | POST /v1/messages model=%s", model)

        r = await self._client.post("/v1/messages", json=payload)
        r.raise_for_status()
        data = r.json()

        content = data.get("content", [])
        if not content:
            raise ValueError("Claude returned empty content")

        return content[0].get("text", "")

    async def aclose(self) -> None:
        """Close the shared HTTP client and release connections."""
        await self._client.aclose()
        logger.debug("ClaudeProvider: HTTP client closed")
