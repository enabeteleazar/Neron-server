"""LLM Manager — orchestration engine with single/parallel/race modes.

Supports:
  - single: one provider, chosen by router, with automatic fallback
  - parallel: all providers via asyncio.gather, best result picked
  - race: asyncio.wait(FIRST_COMPLETED), loser tasks cancelled
  - retry (2 attempts) on provider failure
  - automatic fallback: Ollama → Claude
"""

from __future__ import annotations

import asyncio
import logging

from neron_llm.core.router import LLMRouter
from neron_llm.core.strategy import StrategyEngine
from neron_llm.core.types import LLMRequest, LLMResponse
from neron_llm.providers.base import BaseProvider
from neron_llm.providers.claude import ClaudeProvider
from neron_llm.providers.ollama import OllamaProvider

logger = logging.getLogger("neron_llm.manager")

MAX_RETRIES = 2


class LLMManager:
    """Orchestrates LLM calls across providers with strategy and fallback."""

    def __init__(self):
        self.router = LLMRouter()
        self.strategy = StrategyEngine()
        self.providers: dict[str, BaseProvider] = {
            "ollama": OllamaProvider(),
            "claude": ClaudeProvider(),
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def handle(self, request: LLMRequest) -> LLMResponse:
        """Route, strategize, and execute the request."""
        mode = self.strategy.decide(task=request.task, mode=request.mode)
        model = request.model or self.router.select_model(task=request.task)
        provider_name = self.router.select_provider(provider=request.provider)

        logger.info(
            "Handle: mode=%s, model=%s, provider=%s",
            mode, model, provider_name,
        )

        if mode == "parallel":
            return await self._execute_parallel(request, model)
        elif mode == "race":
            return await self._execute_race(request, model)
        else:
            return await self._execute_single(request, model, provider_name)

    # ------------------------------------------------------------------
    # Mode SINGLE — one provider, retry + fallback
    # ------------------------------------------------------------------

    async def _execute_single(
        self, request: LLMRequest, model: str, provider_name: str,
    ) -> LLMResponse:
        """Execute with a single provider, retry on failure, then fallback."""
        result = await self._call_with_retry(provider_name, request.message, model)
        if result.error is None:
            return result

        # Fallback to next provider in chain
        fallback = self.router.get_fallback_provider(provider_name)
        if fallback and fallback in self.providers:
            logger.warning(
                "Provider '%s' failed after %d retries → falling back to '%s'",
                provider_name, MAX_RETRIES, fallback,
            )
            result = await self._call_with_retry(fallback, request.message, model)

        return result

    # ------------------------------------------------------------------
    # Mode PARALLEL — all providers, pick best result
    # ------------------------------------------------------------------

    async def _execute_parallel(
        self, request: LLMRequest, model: str,
    ) -> LLMResponse:
        """Execute on all providers in parallel, return best result."""
        tasks = [
            self._call_provider(name, provider, request.message, model)
            for name, provider in self.providers.items()
        ]
        results = await asyncio.gather(*tasks)

        valid = [r for r in results if r.error is None]
        if not valid:
            # All failed — return first error
            return results[0] if results else LLMResponse(
                model=model, provider="none", response="", error="All providers failed",
            )

        # Simple scoring: pick the longest response (heuristic for completeness)
        best = max(valid, key=lambda r: len(r.response))
        logger.info(
            "Parallel best: provider=%s, len=%d",
            best.provider, len(best.response),
        )
        return best

    # ------------------------------------------------------------------
    # Mode RACE — first completed wins, others cancelled
    # ------------------------------------------------------------------

    async def _execute_race(
        self, request: LLMRequest, model: str,
    ) -> LLMResponse:
        """Execute on all providers, return first to complete."""
        tasks: dict[asyncio.Task, str] = {}
        for name, provider in self.providers.items():
            task = asyncio.create_task(
                self._call_provider(name, provider, request.message, model),
            )
            tasks[task] = name

        done, pending = await asyncio.wait(
            tasks.keys(), return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel pending tasks
        cancelled: list[str] = []
        for task in pending:
            task.cancel()
            cancelled.append(tasks[task])
        logger.debug("Race: cancelled providers=%s", cancelled)

        # Collect results from completed tasks
        for task in done:
            result = task.result()
            if isinstance(result, LLMResponse) and result.error is None:
                logger.info("Race winner: provider=%s", result.provider)
                return result

        # Winner had error — try other completed tasks
        for task in done:
            result = task.result()
            if isinstance(result, LLMResponse):
                return result

        return LLMResponse(
            model=model, provider="none", response="", error="Race: all providers failed",
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _call_with_retry(
        self, provider_name: str, message: str, model: str,
    ) -> LLMResponse:
        """Call a provider with retry logic (up to MAX_RETRIES attempts)."""
        provider = self.providers.get(provider_name)
        if not provider:
            return LLMResponse(
                model=model, provider=provider_name, response="",
                error=f"Unknown provider: {provider_name}",
            )

        last_result: LLMResponse | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            result = await self._call_provider(provider_name, provider, message, model)
            if result.error is None:
                return result
            logger.warning(
                "Attempt %d/%d failed for '%s': %s",
                attempt, MAX_RETRIES, provider_name, result.error,
            )
            last_result = result

        # All retries exhausted
        return last_result or LLMResponse(
            model=model, provider=provider_name, response="",
            error=f"Provider '{provider_name}' failed after {MAX_RETRIES} attempts",
        )

    async def _call_provider(
        self, name: str, provider: BaseProvider, message: str, model: str,
    ) -> LLMResponse:
        """Call a single provider and wrap result in LLMResponse."""
        try:
            response = await provider.generate(message, model)
            return LLMResponse(model=model, provider=name, response=response, error=None)
        except Exception as exc:
            logger.error("Provider '%s' error: %s", name, exc)
            return LLMResponse(model=model, provider=name, response="", error=str(exc))

    @staticmethod
    def _pick_best(responses: list[LLMResponse]) -> LLMResponse:
        """Simple scoring: prefer non-error, then longest response."""
        valid = [r for r in responses if r.error is None]
        if not valid:
            return responses[0]
        return max(valid, key=lambda r: len(r.response))