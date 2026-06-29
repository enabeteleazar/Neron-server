from __future__ import annotations

import pytest

from core.pipeline.orchestrator import CoreOrchestrator


EXPECTED_DECISION_KEYS = {
    "intent",
    "selected_route",
    "reason",
    "complexity",
    "requires_llm",
    "requires_timer",
    "requires_memory",
    "requires_tool",
    "requires_resolver",
    "requires_agent_factory",
    "requires_goal_pipeline",
    "requires_governor",
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "expected_route"),
    [
        ("Salut Neron", "llm_provider"),
        ("Explique-moi Kubernetes", "llm_provider"),
        ("Quelle est ta mission ?", "identity_provider"),
        ("Comment fonctionnes-tu ?", "identity_provider"),
        ("Quelle heure est-il ?", "timer_engine"),
        ("Mets un minuteur de 10 minutes", "timer_engine"),
        ("Souviens-toi de mon projet Neron", "memory_provider"),
        ("Cree un outil pour surveiller systemd", "goal_engine"),
        ("Analyse cette demande complexe", "goal_engine"),
        ("/goal cree un agent meteo", "goal_pipeline"),
        ("/help", "help_provider"),
    ],
)
async def test_core_orchestrator_is_the_single_route_authority(
    query: str,
    expected_route: str,
):
    orchestrator = CoreOrchestrator()

    decision, _ = await orchestrator.decide(query)

    assert decision.selected_route == expected_route
    assert set(decision.to_dict()) == EXPECTED_DECISION_KEYS
    assert decision.reason
    assert decision.complexity in {"simple", "medium", "complex"}


class FakeAgentRouter:
    def __init__(self) -> None:
        self.calls = []

    async def route(self, intent_result, query, source_channel="api"):
        self.calls.append((intent_result.intent.value, query, source_channel))
        return "reponse llm"


class ForbiddenResolver:
    async def resolve(self, _request):
        raise AssertionError("Resolver must not run for ordinary conversation")


@pytest.mark.asyncio
async def test_orchestrator_does_not_route_everything_to_resolver():
    agent_router = FakeAgentRouter()
    orchestrator = CoreOrchestrator(
        agent_router=agent_router,
        capability_resolver=ForbiddenResolver(),
    )

    result = await orchestrator.handle("Explique-moi Kubernetes")

    assert result.decision.selected_route == "llm_provider"
    assert result.executor == "llm"
    assert result.error == "llm provider unavailable"
    assert agent_router.calls == []


@pytest.mark.asyncio
async def test_help_returns_phase4_sections_without_obsolete_commands():
    class ForbiddenAgentRouter:
        async def route(self, *_args, **_kwargs):
            raise AssertionError("/help must not use the LLM/agent router")

    result = await CoreOrchestrator(agent_router=ForbiddenAgentRouter()).handle(
        "/help"
    )

    assert result.decision.selected_route == "help_provider"
    assert result.executor == "help_provider"
    for section in (
        "🤖 Néron — Commandes disponibles",
        "💬 Conversation",
        "🧠 Orchestration",
        "📊 Système",
        "🧭 Code Awareness",
        "💻 Workspace",
        "🧬 Évolution supervisée",
    ):
        assert section in result.response

    for obsolete_command in (
        "/fix",
        "/review",
        "/goal_status",
        "/projects",
        "/health",
        "/services",
    ):
        assert obsolete_command not in result.response


@pytest.mark.asyncio
async def test_planner_is_not_consulted_during_route_decision(monkeypatch):
    def forbidden_planner(*_args, **_kwargs):
        raise AssertionError("Planner must only be called by an executing pipeline")

    monkeypatch.setattr(
        "goal.planning.planner.AutonomousPlanner.create_plan",
        forbidden_planner,
    )

    decision, _ = await CoreOrchestrator().decide(
        "Analyse cette demande complexe"
    )

    assert decision.selected_route == "goal_engine"


@pytest.mark.asyncio
async def test_orchestrator_routes_timer(monkeypatch):
    class ForbiddenAgentRouter:
        async def route(self, *_args, **_kwargs):
            raise AssertionError("Timer must not use the LLM/agent router")

    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())
    result = await orchestrator.handle("Quelle heure est-il ?")

    assert result.decision.selected_route == "timer_engine"
    assert result.executor == "timer_module"
    assert result.decision.requires_llm is False
    assert result.metadata["source"] == "timer_module"


@pytest.mark.asyncio
async def test_timer_does_not_require_llm():
    decision, _ = await CoreOrchestrator().decide("Quel jour sommes-nous ?")

    assert decision.selected_route == "timer_engine"
    assert decision.requires_timer is True
    assert decision.requires_llm is False


@pytest.mark.asyncio
async def test_orchestrator_routes_identity(monkeypatch):
    calls = []

    async def fake_identity(kind, question=None, *, use_llm=True):
        calls.append((kind, question, use_llm))
        return {
            "response": "Je suis Néron.",
            "agent": "identity_module",
            "source": "identity_module:test",
            "llm_used": False,
        }

    monkeypatch.setattr(
        "core.pipeline.orchestrator.build_identity_response_async",
        fake_identity,
    )

    result = await CoreOrchestrator().handle("Qui es-tu ?")

    assert result.decision.selected_route == "identity_provider"
    assert result.executor == "identity_module"
    assert calls == [("identity_short", "Qui es-tu ?", False)]
    assert result.metadata["identity_llm_used"] is False


@pytest.mark.asyncio
async def test_orchestrator_routes_status(monkeypatch):
    calls = []

    async def fake_status(kind, *, question=None, use_llm=True):
        calls.append((kind, question, use_llm))
        return {
            "response": "Je fonctionne normalement.",
            "agent": "status_module",
            "source": "status_module",
            "status_kind": kind,
            "status": {"global_status": "healthy"},
            "llm_used": False,
        }

    monkeypatch.setattr(
        "core.pipeline.orchestrator.build_status_response_async",
        fake_status,
    )

    result = await CoreOrchestrator().handle("Comment vas-tu ?")

    assert result.decision.selected_route == "status_provider"
    assert result.executor == "status_module"
    assert calls == [("health_query", "Comment vas-tu ?", False)]
    assert result.metadata["status_llm_used"] is False


@pytest.mark.asyncio
async def test_orchestrator_routes_location_to_status():
    decision, _ = await CoreOrchestrator().decide("Où es-tu ?")

    assert decision.selected_route == "status_provider"
    assert decision.requires_llm is False


@pytest.mark.asyncio
async def test_orchestrator_routes_goal():
    decision, _ = await CoreOrchestrator().decide(
        "Créer un agent nommé phase4_agent"
    )

    assert decision.selected_route == "goal_engine"
    assert decision.requires_goal_pipeline is True
    assert decision.requires_agent_factory is False


@pytest.mark.asyncio
async def test_goal_pipeline_only_runs_for_explicit_core_decision():
    class FakeGoalPipeline:
        def __init__(self) -> None:
            self.calls = []

        async def run_goal(self, objective, source="api"):
            self.calls.append((objective, source))
            return {"status": "plan_finished", "response": "objectif termine"}

    pipeline = FakeGoalPipeline()
    orchestrator = CoreOrchestrator(
        goal_orchestrator_factory=lambda: pipeline,
    )

    result = await orchestrator.handle(
        "/goal cree un agent meteo",
        source_channel="telegram",
    )

    assert result.decision.selected_route == "goal_pipeline"
    assert pipeline.calls == [("cree un agent meteo", "telegram")]
    assert result.response == "objectif termine"
