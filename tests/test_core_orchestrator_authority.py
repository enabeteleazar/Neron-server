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
        ("Souviens-toi de mon projet Neron", "memory_engine"),
        ("Cree un outil pour surveiller systemd", "agent_factory"),
        ("Analyse cette demande complexe", "resolver"),
        ("/goal cree un agent meteo", "goal_pipeline"),
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
async def test_resolver_is_not_used_by_default():
    agent_router = FakeAgentRouter()
    orchestrator = CoreOrchestrator(
        agent_router=agent_router,
        capability_resolver=ForbiddenResolver(),
    )

    result = await orchestrator.handle("Explique-moi Kubernetes")

    assert result.response == "reponse llm"
    assert result.decision.selected_route == "llm_provider"
    assert result.executor == "llm_agent"
    assert agent_router.calls == [
        ("conversation", "Explique-moi Kubernetes", "api")
    ]


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

    assert decision.selected_route == "resolver"


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
