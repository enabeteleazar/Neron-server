"""Tests for neron_llm v1.0 — parallel, race, single, strategy, fallback, retry.

Run with: pytest tests/ -v
"""

from __future__ import annotations

import asyncio
import time

import pytest

from neron_llm.core.manager import LLMManager, MAX_RETRIES
from neron_llm.core.router import LLMRouter
from neron_llm.core.strategy import StrategyEngine
from neron_llm.core.types import LLMRequest, LLMResponse
from neron_llm.providers.base import BaseProvider


# ---------------------------------------------------------------------------
# Fake providers (async — conform to BaseProvider)
# ---------------------------------------------------------------------------


class SlowProvider(BaseProvider):
    """Fake provider simulating a network call of known duration."""

    def __init__(self, name: str, delay: float):
        self.name = name
        self.delay = delay

    async def generate(self, message: str, model: str) -> str:
        await asyncio.sleep(self.delay)
        return f"[{self.name}] response after {self.delay}s"


class FailingProvider(BaseProvider):
    """Fake provider that always raises an exception."""

    def __init__(self, fail_count: int = 999):
        self.fail_count = fail_count
        self.call_count = 0

    async def generate(self, message: str, model: str) -> str:
        self.call_count += 1
        if self.call_count <= self.fail_count:
            raise RuntimeError(f"Provider error (attempt {self.call_count})")
        return "recovered"


class RecoveringProvider(BaseProvider):
    """Fails on first attempt, succeeds on second (tests retry)."""

    def __init__(self):
        self.call_count = 0

    async def generate(self, message: str, model: str) -> str:
        self.call_count += 1
        if self.call_count == 1:
            raise RuntimeError("First attempt failed")
        return f"Success on attempt {self.call_count}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_manager_with_slow_providers() -> LLMManager:
    mgr = LLMManager()
    mgr.providers = {
        "fast": SlowProvider("fast", 0.2),
        "medium": SlowProvider("medium", 0.3),
        "slow": SlowProvider("slow", 0.4),
    }
    return mgr


def make_request(
    message: str = "test",
    task: str = "default",
    mode: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> LLMRequest:
    return LLMRequest(message=message, task=task, mode=mode, provider=provider, model=model)


# ---------------------------------------------------------------------------
# Strategy tests
# ---------------------------------------------------------------------------


def test_strategy_explicit_mode():
    """Explicit mode takes priority over task-based strategy."""
    engine = StrategyEngine()
    assert engine.decide(task="code", mode="single") == "single"
    assert engine.decide(task="chat", mode="parallel") == "parallel"


def test_strategy_task_based():
    """Task determines mode when no explicit mode is set."""
    engine = StrategyEngine()
    assert engine.decide(task="code") == "parallel"
    assert engine.decide(task="chat") == "race"
    assert engine.decide(task="fast") == "single"


def test_strategy_default():
    """Unknown task falls back to 'single'."""
    engine = StrategyEngine()
    assert engine.decide(task="unknown") == "single"
    assert engine.decide() == "single"


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------


def test_router_select_model():
    """Router selects model based on task from config."""
    router = LLMRouter()
    # These depend on neron.yaml being present
    model = router.select_model("default")
    assert isinstance(model, str)
    assert len(model) > 0


def test_router_select_provider():
    """Explicit provider takes priority."""
    router = LLMRouter()
    assert router.select_provider("claude") == "claude"
    assert router.select_provider() == "ollama"  # default


def test_router_fallback_chain():
    """Fallback provider chain works correctly."""
    router = LLMRouter()
    assert router.get_fallback_provider("ollama") == "claude"
    assert router.get_fallback_provider("claude") is None
    assert router.get_fallback_provider("unknown") is None


# ---------------------------------------------------------------------------
# Execution mode tests
# ---------------------------------------------------------------------------


def test_parallel_execution():
    """Providers run in parallel — total time ≈ max(delay), not sum(delay)."""
    mgr = make_manager_with_slow_providers()
    req = make_request(mode="parallel")

    start = time.perf_counter()
    result = asyncio.run(mgr.handle(req))
    elapsed = time.perf_counter() - start

    # Parallel: ≈ 0.4s | Sequential: ≈ 0.9s
    assert elapsed < 0.6, (
        f"NOT PARALLEL! Time={elapsed:.2f}s, expected < 0.6s. "
        f"Sequential would be ~0.9s."
    )
    assert result.error is None
    assert len(result.response) > 0

    print(f"\n  PARALLEL confirmed: {elapsed:.3f}s (sequential ~0.9s)")


def test_race_execution():
    """In race mode, the fastest provider wins and others are cancelled."""
    mgr = make_manager_with_slow_providers()
    req = make_request(mode="race")

    start = time.perf_counter()
    result = asyncio.run(mgr.handle(req))
    elapsed = time.perf_counter() - start

    assert elapsed < 0.35, (
        f"RACE too slow: {elapsed:.2f}s. 'fast' (0.2s) should have won."
    )
    assert result.error is None
    assert "fast" in result.response

    print(f"\n  RACE confirmed: {elapsed:.3f}s — winner={result.provider}")


def test_single_execution():
    """Single mode returns structured LLMResponse."""
    mgr = LLMManager()
    mgr.providers = {"ollama": SlowProvider("ollama", 0.05)}
    mgr.router.select_provider = lambda provider=None: "ollama"
    mgr.router.select_model = lambda task=None: "test-model"

    req = make_request(mode="single")
    result = asyncio.run(mgr.handle(req))

    assert isinstance(result, LLMResponse)
    assert result.provider == "ollama"
    assert result.model == "test-model"
    assert result.error is None
    assert "ollama" in result.response

    print(f"\n  SINGLE structured: {result}")


def test_sequential_baseline():
    """Sequential baseline — 3 calls × 0.2s should take > 0.4s."""
    mgr = LLMManager()
    mgr.providers = {"fast": SlowProvider("fast", 0.2)}
    mgr.router.select_provider = lambda provider=None: "fast"
    mgr.router.select_model = lambda task=None: "test"

    req = make_request(mode="single")

    start = time.perf_counter()
    asyncio.run(mgr.handle(req))
    asyncio.run(mgr.handle(req))
    asyncio.run(mgr.handle(req))
    elapsed = time.perf_counter() - start

    assert elapsed > 0.4, f"Sequential too fast: {elapsed:.2f}s, expected > 0.4s"

    print(f"\n  SEQUENTIAL baseline: {elapsed:.3f}s (3 × 0.2s)")


# ---------------------------------------------------------------------------
# Fallback + retry tests
# ---------------------------------------------------------------------------


def test_fallback_on_failure():
    """If primary provider fails, fallback provider is used."""
    mgr = LLMManager()
    mgr.providers = {
        "ollama": FailingProvider(),  # always fails
        "claude": SlowProvider("claude", 0.05),  # succeeds
    }

    req = make_request(mode="single", provider="ollama")
    result = asyncio.run(mgr.handle(req))

    # Should fallback to claude
    assert result.provider == "claude"
    assert result.error is None
    assert "claude" in result.response

    print(f"\n  FALLBACK confirmed: ollama → claude, result={result.provider}")


def test_retry_then_success():
    """Provider that fails once but succeeds on retry."""
    mgr = LLMManager()
    recovering = RecoveringProvider()
    mgr.providers = {
        "ollama": recovering,
        "claude": SlowProvider("claude", 0.05),
    }
    mgr.router.select_provider = lambda provider=None: "ollama"
    mgr.router.select_model = lambda task=None: "test"

    req = make_request(mode="single")
    result = asyncio.run(mgr.handle(req))

    assert result.error is None
    assert result.provider == "ollama"
    assert recovering.call_count == 2  # failed once, succeeded on retry

    print(f"\n  RETRY confirmed: 2 attempts, success on retry")


def test_all_providers_fail():
    """When all providers fail, error is returned."""
    mgr = LLMManager()
    mgr.providers = {
        "ollama": FailingProvider(),
        "claude": FailingProvider(),
    }

    req = make_request(mode="single", provider="ollama")
    result = asyncio.run(mgr.handle(req))

    assert result.error is not None
    assert "error" in result.error.lower() or "failed" in result.error.lower()

    print(f"\n  ALL-FAIL handled: error={result.error}")


def test_parallel_tolerates_failing_provider():
    """In parallel mode, a failing provider doesn't crash others."""
    mgr = LLMManager()
    mgr.providers = {
        "good": SlowProvider("good", 0.1),
        "failing": FailingProvider(),
    }

    req = make_request(mode="parallel")
    result = asyncio.run(mgr.handle(req))

    assert result.error is None
    assert "good" in result.response

    print(f"\n  PARALLEL tolerance: good provider result returned")


# ---------------------------------------------------------------------------
# Standardized response format tests
# ---------------------------------------------------------------------------


def test_response_format():
    """Every response follows the LLMResponse format."""
    mgr = LLMManager()
    mgr.providers = {"ollama": SlowProvider("ollama", 0.05)}
    mgr.router.select_provider = lambda provider=None: "ollama"
    mgr.router.select_model = lambda task=None: "test-model"

    for mode in ["single", "parallel", "race"]:
        req = make_request(mode=mode)
        result = asyncio.run(mgr.handle(req))

        assert isinstance(result, LLMResponse)
        assert hasattr(result, "model")
        assert hasattr(result, "provider")
        assert hasattr(result, "response")
        assert hasattr(result, "error")

    print(f"\n  RESPONSE FORMAT consistent across all modes")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_strategy_explicit_mode()
    test_strategy_task_based()
    test_strategy_default()
    test_router_select_model()
    test_router_select_provider()
    test_router_fallback_chain()
    test_parallel_execution()
    test_race_execution()
    test_single_execution()
    test_sequential_baseline()
    test_fallback_on_failure()
    test_retry_then_success()
    test_all_providers_fail()
    test_parallel_tolerates_failing_provider()
    test_response_format()
    print("\n  All tests passed — neron_llm v1.0 is production-ready.")