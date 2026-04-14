"""Intelligent LLM router — selects model and provider based on config.

Reads from the 'routing' (or legacy 'model_map') section of neron.yaml.
Provides automatic fallback to the next provider on failure.
"""

from __future__ import annotations

import logging

from neron_llm.config import get_llm_config, get_routing_config

logger = logging.getLogger("neron_llm.router")

FALLBACK_MODEL = "mistral:latest"

# Provider priority chain — used for fallback
PROVIDER_CHAIN: list[str] = ["ollama", "claude"]


class LLMRouter:
    """Selects the model and provider for a given request."""

    def __init__(self):
        self._routing = get_routing_config()
        self._llm_config = get_llm_config()

    def select_model(self, task: str | None = None) -> str:
        """Select model based on task. Falls back: task → default → FALLBACK_MODEL."""
        if task and task in self._routing:
            model = self._routing[task]
            logger.debug("Router: task='%s' → model='%s'", task, model)
            return model

        model = self._routing.get("default", FALLBACK_MODEL)
        logger.debug("Router: fallback → model='%s'", model)
        return model

    def select_provider(self, provider: str | None = None) -> str:
        """Select provider. Priority: explicit > config default > 'ollama'."""
        if provider:
            logger.debug("Router: explicit provider='%s'", provider)
            return provider

        default = self._llm_config.get("default_provider", "ollama")
        logger.debug("Router: default provider='%s'", default)
        return default

    def get_fallback_provider(self, current: str) -> str | None:
        """Return the next provider in the fallback chain after `current`.

        Returns None if `current` is the last provider or not in the chain.
        """
        try:
            idx = PROVIDER_CHAIN.index(current)
            if idx + 1 < len(PROVIDER_CHAIN):
                next_provider = PROVIDER_CHAIN[idx + 1]
                logger.debug("Router: fallback %s → %s", current, next_provider)
                return next_provider
        except ValueError:
            pass
        return None