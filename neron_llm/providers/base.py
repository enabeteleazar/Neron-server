"""Base provider interface for all LLM backends.

Every provider MUST be async to enable parallel and race execution
without blocking the event loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate(self, message: str, model: str) -> str:
        """Send a message to the LLM and return the text response.

        Raises:
            Exception: On timeout, HTTP error, or any failure.
                      The manager catches exceptions and formats them
                      into LLMResponse(error=...).
        """
        ...