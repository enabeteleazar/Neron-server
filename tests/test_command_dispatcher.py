from __future__ import annotations

from pathlib import Path

from core.orchestration.command_dispatcher import NeronCommandDispatcher


# Phase 2E : `FakeGoalOrchestrator` a ete retire. Il simulait un orchestrateur
# Goal en process, que `CoreOrchestrator` n appelle plus depuis la phase 3 (le
# service goal est joint en HTTP). Il etait donc injecte mais jamais consulte,
# ce qui laissait le test partir sur le reseau. Voir `_FakeGoalClient`.


class FakeEvolutionSupervisor:
    def status(self) -> dict:
        return {"active_run": {"run_id": "run-1", "status": "running", "current_step": "codex", "progress": 25}}


class _FakeGoalClient:
    """Isole le test du reseau : sans cela il POSTait un vrai objectif sur goal:8030.

    `CoreOrchestrator.run_goal` n utilise plus `goal_orchestrator_factory`
    (deprecie depuis la phase 3, ignore avec un avertissement) : il appelle
    `GoalClient` en HTTP. Le test partait donc jusqu au service reel, lancait
    une vraie execution et echouait en timeout.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def run_goal(self, objective: str, *, source: str = "api") -> dict:
        self.calls.append((objective, source))
        return {
            "status": "plan_finished",
            "plan": {
                "id": "plan-12345678",
                "goal": objective,
                "risk": {"risk_level": "low", "risk_score": 5},
            },
        }


async def test_dispatcher_routes_goal_request_without_telegram_orchestrator_coupling(
    monkeypatch,
):
    goal_client = _FakeGoalClient()
    monkeypatch.setattr(
        "server.common.goal_client.get_goal_client", lambda: goal_client
    )
    dispatcher = NeronCommandDispatcher()

    result = await dispatcher.dispatch(
        {
            "source": "telegram",
            "type": "goal_request",
            "payload": "Créer un agent météo",
            "user_id": "chat-1",
        }
    )

    assert result["status"] == "plan_finished"
    # L objectif part vers le service goal, pas vers un orchestrateur en process.
    assert goal_client.calls == [("Créer un agent météo", "telegram")]
    assert "Objectif reçu" in result["messages"][0]


async def test_dispatcher_routes_evolution_status():
    dispatcher = NeronCommandDispatcher(evolution_supervisor_factory=lambda: FakeEvolutionSupervisor())

    result = await dispatcher.dispatch(
        {
            "source": "telegram",
            "type": "evolution_text",
            "payload": "/evolution_status",
            "user_id": "chat-1",
        }
    )

    assert result["status"] == "ok"
    assert "Run : run-1" in result["messages"][0]


def test_telegram_agent_does_not_import_internal_orchestrators_directly():
    source = (
        Path(__file__).resolve().parents[1]
        / "server"
        / "core"
        / "agents"
        / "communication"
        / "telegram_agent.py"
    ).read_text(encoding="utf-8")

    assert "goal.goals.goal_orchestrator" not in source
    assert "modules.evolution.supervisor" not in source
