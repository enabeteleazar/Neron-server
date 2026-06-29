from __future__ import annotations

import pytest

from core.pipeline.orchestrator import CoreOrchestrator
from core.providers.models import ProviderInfo, ProviderResponse


class ForbiddenAgentRouter:
    async def route(self, *_args, **_kwargs):
        raise AssertionError("LLM traffic must go through LLMProvider")


class FakeLLMProvider:
    name = "llm"
    type = "llm"
    status = "healthy"
    capabilities = ["health", "generate", "status"]

    def __init__(self) -> None:
        self.calls: list[object] = []

    async def health(self):
        return ProviderResponse(
            provider=self.name,
            action="health",
            status="healthy",
            result={"status": "ok", "service": "fake_llm"},
        )

    async def execute(self, request):
        self.calls.append(request)
        return ProviderResponse(
            provider=self.name,
            action=request.action,
            status="healthy",
            result={
                "text": "NéronOS est un kernel personnel orchestrant services, mémoire et providers.",
                "model": "fake-model",
                "latency_ms": 7,
                "warning": None,
            },
        )


class FakeProviderRegistry:
    def __init__(self, provider: FakeLLMProvider) -> None:
        self.provider = provider

    def by_type(self, provider_type):
        if provider_type != "llm":
            return []
        return [
            ProviderInfo(
                name=self.provider.name,
                type="llm",
                status="healthy",
                capabilities=["health", "generate", "status"],
            )
        ]

    def get(self, name):
        if name == self.provider.name:
            return self.provider
        return None


@pytest.mark.asyncio
async def test_conversation_routes_to_llm_provider(monkeypatch):
    provider = FakeLLMProvider()
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        FakeProviderRegistry(provider),
    )

    result = await CoreOrchestrator(agent_router=ForbiddenAgentRouter()).handle(
        "Explique-moi en une phrase ce qu’est NéronOS."
    )

    assert result.decision.selected_route == "llm_provider"
    assert result.decision.requires_llm is True
    assert result.executor == "llm"
    assert result.model == "fake-model"
    assert result.response.startswith("NéronOS est un kernel")
    assert provider.calls
    assert provider.calls[0].action == "generate"
    assert provider.calls[0].payload["prompt"] == "Explique-moi en une phrase ce qu’est NéronOS."
    assert result.metadata["selected_route"] == "llm_provider"
    assert result.metadata["executor"] == "llm"
    assert result.metadata["provider_status"] == "healthy"
    assert result.metadata["llm_used"] is True
    assert result.metadata["llm_provider"] == "llm"
    assert result.metadata["llm_action"] == "generate"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "Qui es-tu ?",
        "Quels services fonctionnent ?",
        "Quelle heure est-il ?",
        "Mémorise que le Provider Memory fonctionne.",
        "Recherche Phase 2",
    ],
)
async def test_local_intents_do_not_use_llm_provider(monkeypatch, query: str):
    provider = FakeLLMProvider()
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        FakeProviderRegistry(provider),
    )

    await CoreOrchestrator(agent_router=ForbiddenAgentRouter()).handle(query)

    assert provider.calls == []
