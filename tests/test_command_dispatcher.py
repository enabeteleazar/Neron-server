from __future__ import annotations

from pathlib import Path

from core.orchestration.command_dispatcher import NeronCommandDispatcher


class FakeGoalOrchestrator:
    def __init__(self) -> None:
        self.goal_requests: list[tuple[str, str]] = []
        self.executed_approvals: list[tuple[str, str]] = []

    async def run_goal(self, objective: str, source: str = "system") -> dict:
        self.goal_requests.append((objective, source))
        return {
            "status": "plan_finished",
            "plan": {
                "id": "plan-12345678",
                "goal": objective,
                "risk": {"risk_level": "low", "risk_score": 5},
            },
        }

    def find_plan(self, plan_id: str) -> dict | None:
        if plan_id == "missing":
            return None
        return {"id": "plan-12345678", "goal": "objectif", "approved": True}

    async def execute_approved_plan(self, plan_id: str, approved_by: str = "system") -> dict:
        self.executed_approvals.append((plan_id, approved_by))
        return {"status": "plan_finished", "plan": {"id": "plan-12345678", "goal": "objectif"}}


class FakeEvolutionSupervisor:
    def status(self) -> dict:
        return {"active_run": {"run_id": "run-1", "status": "running", "current_step": "codex", "progress": 25}}


async def test_dispatcher_routes_goal_request_without_telegram_orchestrator_coupling():
    orchestrator = FakeGoalOrchestrator()
    dispatcher = NeronCommandDispatcher(goal_orchestrator_factory=lambda: orchestrator)

    result = await dispatcher.dispatch(
        {
            "source": "telegram",
            "type": "goal_request",
            "payload": "Créer un agent météo",
            "user_id": "chat-1",
        }
    )

    assert result["status"] == "plan_finished"
    assert orchestrator.goal_requests == [("Créer un agent météo", "telegram")]
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
