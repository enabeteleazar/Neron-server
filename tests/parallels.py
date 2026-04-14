"""
Tests qui PROUVENT que les agents tournent en parallèle (et pas en séquentiel).

Principe :
  - On crée 3 providers factices qui sleepent respectivement 0.2s, 0.3s, 0.4s
  - Si on les exécute EN PARALLÈLE : temps total ≈ 0.4s (le plus lent)
  - Si on les exécute EN SÉQUENTIEL : temps total ≈ 0.9s (somme de tous)

Les SlowProvider sont désormais async, conformément à BaseProvider.
"""
import asyncio
import time

import pytest

from neron_llm.core.manager import LLMManager
from neron_llm.core.types import LLMRequest
from neron_llm.providers.base import BaseProvider


# ---------------------------------------------------------------------------
# Providers factices (async — conforme à BaseProvider)
# ---------------------------------------------------------------------------

class SlowProvider(BaseProvider):
    """Provider factice simulant un appel réseau de durée connue."""

    def __init__(self, name: str, delay: float):
        self.name = name
        self.delay = delay

    async def generate(self, message: str, model: str) -> str:
        await asyncio.sleep(self.delay)
        return f"[{self.name}] réponse après {self.delay}s"


class FailingProvider(BaseProvider):
    """Provider factice qui lève toujours une exception."""

    async def generate(self, message: str, model: str) -> str:
        raise RuntimeError("Provider en erreur")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_manager_with_slow_providers() -> LLMManager:
    mgr = LLMManager()
    mgr.providers = {
        "fast":   SlowProvider("fast",   0.2),
        "medium": SlowProvider("medium", 0.3),
        "slow":   SlowProvider("slow",   0.4),
    }
    return mgr


def make_request(mode: str = "single") -> LLMRequest:
    return LLMRequest(message="test", task="default", mode=mode)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parallel_execution():
    """Les providers doivent tourner en parallèle — temps total ≈ max(delays), pas sum(delays)."""
    mgr = make_manager_with_slow_providers()
    req = make_request("parallel")

    start = time.perf_counter()
    result = asyncio.run(mgr.generate_parallel(req))
    elapsed = time.perf_counter() - start

    # Parallèle : ≈ 0.4s | Séquentiel : ≈ 0.9s
    assert elapsed < 0.6, (
        f"EXÉCUTION NON PARALLÈLE ! Temps={elapsed:.2f}s, attendu < 0.6s. "
        f"Séquentiel aurait pris ~0.9s."
    )
    assert "fast"   in result.results
    assert "medium" in result.results
    assert "slow"   in result.results

    print(f"\n✅ PARALLÈLE confirmé : {elapsed:.3f}s (séquentiel ≈ 0.9s)")
    print(f"   Résultats : {result.results}")


def test_race_execution():
    """En mode race, le provider le plus rapide gagne et les autres sont annulés."""
    mgr = make_manager_with_slow_providers()
    req = make_request("race")

    start = time.perf_counter()
    result = asyncio.run(mgr.generate_race(req))
    elapsed = time.perf_counter() - start

    assert elapsed < 0.35, (
        f"RACE trop lent : {elapsed:.2f}s. 'fast' (0.2s) aurait dû gagner."
    )
    assert result.winner == "fast"
    assert "fast" in result.response

    print(f"\n✅ RACE confirmé : {elapsed:.3f}s — gagnant={result.winner}")


def test_sequential_baseline():
    """Baseline : 3 appels séquentiels doivent prendre ~0.6s (3 × 0.2s)."""
    mgr = LLMManager()
    mgr.providers = {"fast": SlowProvider("fast", 0.2)}
    # On force le router à sélectionner "fast"
    mgr.router.select_provider = lambda req: "fast"

    req = make_request("single")

    start = time.perf_counter()
    asyncio.run(mgr.generate(req))
    asyncio.run(mgr.generate(req))
    asyncio.run(mgr.generate(req))
    elapsed = time.perf_counter() - start

    assert elapsed > 0.4, (
        f"Séquentiel trop rapide : {elapsed:.2f}s, attendu > 0.4s"
    )
    print(f"\n✅ SÉQUENTIEL baseline : {elapsed:.3f}s (3 × 0.2s)")


def test_parallel_tolerates_failing_provider():
    """En mode parallel, un provider en erreur ne doit pas faire planter les autres."""
    mgr = LLMManager()
    mgr.providers = {
        "good":    SlowProvider("good", 0.1),
        "failing": FailingProvider(),
    }

    req = make_request("parallel")
    result = asyncio.run(mgr.generate_parallel(req))

    assert "good" in result.results
    assert "failing" in result.results
    assert "[ERREUR failing]" in result.results["failing"]
    assert "good" in result.results["good"]

    print(f"\n✅ PARALLEL tolérance erreur : {result.results}")


def test_single_returns_structured_response():
    """Le mode single retourne un LLMResponse correctement structuré."""
    mgr = LLMManager()
    mgr.providers = {"ollama": SlowProvider("ollama", 0.05)}
    mgr.router.select_provider = lambda req: "ollama"
    mgr.router.select_model = lambda task: "test-model"

    req = make_request("single")
    result = asyncio.run(mgr.generate(req))

    assert result.provider == "ollama"
    assert result.model == "test-model"
    assert "ollama" in result.response

    print(f"\n✅ SINGLE structuré : {result}")


# ---------------------------------------------------------------------------
# Entrypoint direct
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_sequential_baseline()
    test_parallel_execution()
    test_race_execution()
    test_parallel_tolerates_failing_provider()
    test_single_returns_structured_response()
    print("\n🎯 Tous les tests passés — le parallélisme est RÉEL, pas simulé.")
