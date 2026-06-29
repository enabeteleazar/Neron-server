from __future__ import annotations

import pytest

from core.a2a import A2AClient
from core.goal_engine import (
    AgentRegistry,
    DIAGNOSTIC_AGENT_CARD,
    GoalEngine,
    GoalRequest,
    diagnostic_agent_handler,
)
from core.providers.models import ProviderRequest, ProviderResponse
from core.providers.registry import ProviderRegistry


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class MemoryProvider:
    name = "memory"
    type = "memory"
    status = "healthy"
    capabilities = ["remember"]

    def __init__(self):
        self.requests: list[ProviderRequest] = []

    async def health(self):
        return ProviderResponse(provider="memory", action="health", status="healthy")

    async def execute(self, request):
        self.requests.append(request)
        return ProviderResponse(provider="memory", action=request.action, status="healthy")


async def test_real_diagnostic_agent_runs_through_a2a_and_is_learned():
    agents = AgentRegistry(runtime=type("Runtime", (), {
        "registry": type("Registry", (), {"list_agent_records": lambda self: []})()
    })())
    a2a = A2AClient()
    agents.register(DIAGNOSTIC_AGENT_CARD)
    a2a.register_handler(DIAGNOSTIC_AGENT_CARD, diagnostic_agent_handler)
    memory = MemoryProvider()
    providers = ProviderRegistry()
    providers.register(memory)
    engine = GoalEngine(providers=providers, agents=agents, a2a=a2a)

    result = await engine.execute(
        GoalRequest(objective="Utilise l’agent de diagnostic pour vérifier l’état de Néron.")
    )

    assert result.goal_status == "completed"
    assert result.agent_found is True
    assert result.agent_creation_required is False
    assert result.a2a_used is True
    assert result.verification.ok is True
    assert result.execution.a2a_response.status == "completed"
    assert result.execution.a2a_response.result["diagnostic_status"] == "healthy"
    assert result.memory_learned is True
    assert memory.requests[-1].action == "remember"
