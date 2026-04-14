"""Claude (Anthropic) provider — async HTTP via httpx.AsyncClient.

API key is read from ANTHROPIC_API_KEY env var or from neron.yaml.

Config (neron.yaml → llm section):
    claude_api_key: sk-ant-...
    claude_max_tokens: 1024
    timeout: 300
    temperature: 0.7
"""

from __future__ import annotations

import logging
import os

import httpx

from neron_llm.config import get_llm_config
from neron_llm.providers.base import BaseProvider

logger = logging.getLogger("neron_llm.claude")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class ClaudeProvider(BaseProvider):
    """Async provider for the Anthropic Claude API."""

    def __init__(self):
        cfg = get_llm_config()
        self.api_key: str = (
            os.getenv("ANTHROPIC_API_KEY")
            or cfg.get("claude_api_key", "")
        )
        self.max_tokens: int = int(cfg.get("claude_max_tokens", 1024))
        self.timeout: float = float(cfg.get("timeout", 300))
        self.temperature: float = float(cfg.get("temperature", 0.7))

        if not self.api_key:
            logger.warning(
                "ClaudeProvider: ANTHROPIC_API_KEY not set — calls will raise."
            )

    async def generate(self, message: str, model: str) -> str:
        """Generate a response via the Anthropic Messages API.

        Raises:
            ValueError: If API key is missing or response is empty.
            httpx.TimeoutException: On timeout.
            httpx.HTTPStatusError: On HTTP 4xx/5xx.
            Exception: On any other failure.
        """
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": message}],
        }

        logger.debug("claude | POST %s model=%s", ANTHROPIC_API_URL, model)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        content = data.get("content", [])
        if not content:
            raise ValueError("Claude returned empty content")

        return content[0].get("text", "")