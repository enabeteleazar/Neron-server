# providers/base.py

Base provider interface for all LLM backends.

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

    async def aclose(self) -> None:
        """Release long-lived resources (e.g. shared HTTP client).

        Called by LLMManager.aclose() at application shutdown.
        Default is a no-op — override in providers that hold connections.
        """
        pass
