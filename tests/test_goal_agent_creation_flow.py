from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from core.agent_factory.agent_creator import AgentCreator
from core.cognitive import critic_engine
from core.goals import goal_manager, persistence, routes as goal_routes
from core.goals.goal_orchestrator import GoalOrchestrator
from core.planning.executor import PlanExecutor
from core.planning.storage import PlanStorage
from core.task_system import task_manager
from core.task_system.task_executor import TaskExecutor
from core.task_system.task_manager import TaskManager


def _build_orchestrator(tmp_path: Path, monkeypatch, notifications: list[tuple[str, str]]) -> GoalOrchestrator:
    data_dir = tmp_path / "data"
    project_root = tmp_path / "project"

    monkeypatch.setattr(persistence, "GOALS_PATH", data_dir / "goals_state.json")
    monkeypatch.setattr(task_manager, "TASKS_FILE", data_dir / "tasks.json")
    monkeypatch.setattr(critic_engine, "CRITIC_HISTORY_PATH", data_dir / "critic_history.jsonl")
    monkeypatch.setattr(goal_manager, "_GOAL_MANAGER", None)
    monkeypatch.setattr(task_manager, "_task_manager", None)
    monkeypatch.setattr(critic_engine, "_critic_engine", None)

    async def notifier(message: str, level: str = "info") -> None:
        notifications.append((message, level))

    storage = PlanStorage(data_dir / "plans.jsonl")
    agent_creator = AgentCreator(
        proposals_path=data_dir / "agent_creator_proposals.jsonl",
        project_root=project_root,
    )
    executor = PlanExecutor(project_root=project_root)
    orchestrator = GoalOrchestrator(storage=storage, notifier=notifier)
    orchestrator.storage = storage
    orchestrator.task_manager = TaskManager()
    orchestrator.task_executor = TaskExecutor(
        plan_executor=executor,
        storage=storage,
        agent_creator=agent_creator,
    )
    return orchestrator


def test_goal_triggers_planner_and_agent_creator_proposal(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        notifications: list[tuple[str, str]] = []
        orchestrator = _build_orchestrator(tmp_path, monkeypatch, notifications)

        result = asyncio.run(
            orchestrator.run_goal(
                "Créer un agent météo capable de répondre à une demande météo simple.",
                source="api",
            )
        )

        assert result["status"] == "plan_finished"
        assert result["goal_id"]
        assert result["planner_called"] is True
        assert result["plan_id"]
        assert result["plan"]["steps"]
        assert result["agent_creator_called"] is True
        assert result["agent_request_id"]

        proposal = result["proposal"]
        assert proposal["agent_name"] == "weather_agent"
        assert proposal["required_capabilities"] == [
            "parse_weather_request",
            "fetch_weather_data",
            "format_weather_response",
        ]
        assert proposal["proposed_files"] == [
            "workspace/agents/weather_agent.py",
            "tests/test_weather_agent.py",
        ]
        assert proposal["risk_level"] == "low"
        assert proposal["status"] == "pending_human_validation"
        assert proposal["created_from_goal_id"] == result["goal_id"]
        assert proposal["created_from_plan_id"] == result["plan_id"]
        assert proposal["human_validation_required"] is True
        assert proposal["code_execution_allowed"] is False
        assert proposal["applied_to_core"] is False

        assert not (tmp_path / "project" / "workspace" / "agents" / "weather_agent.py").exists()
        assert not (tmp_path / "project" / "core" / "agents" / "weather_agent.py").exists()

        proposals_path = tmp_path / "data" / "agent_creator_proposals.jsonl"
        assert proposals_path.exists()
        assert "weather_agent" in proposals_path.read_text(encoding="utf-8")


def test_unknown_actions_do_not_finish_functionally(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        notifications: list[tuple[str, str]] = []
        orchestrator = _build_orchestrator(tmp_path, monkeypatch, notifications)

        plan = {
            "id": "unknown-plan",
            "goal": "objectif sans action exécutable",
            "approved": True,
            "approval_required": False,
            "risk": {"risk_level": "low", "risk_score": 0, "execution_allowed": True},
            "steps": [
                {
                    "title": "Étape inconnue",
                    "description": "Ne doit pas être considérée comme réussie.",
                    "agent": "unknown_agent",
                    "action": "unknown_action",
                }
            ],
        }
        orchestrator.storage.save(plan)
        orchestrator.task_manager.create_tasks_from_plan(plan)

        result = asyncio.run(orchestrator.execute_plan(plan, approved_by="test"))

        assert result["status"] == "partial"
        assert result["plan"]["status"] == "partial"
        assert result["plan"]["tasks_completed"] is False
        assert result["plan"]["task_counts"] == {"total": 1, "completed": 0, "skipped": 1, "failed": 0}
        assert not result["plan"].get("agent_creation_proposal")
        assert "Aucune tâche exécutable" in result["plan"]["error"]


async def test_existing_public_route_handlers_remain_callable(monkeypatch):
    import logging
    import os
    from pathlib import Path

    from core.api import self_model_context_routes

    monkeypatch.setattr(Path, "mkdir", lambda self, parents=False, exist_ok=False: None)
    monkeypatch.setattr(os, "access", lambda path, mode: True)
    monkeypatch.setattr(
        "logging.handlers.RotatingFileHandler",
        lambda *args, **kwargs: logging.NullHandler(),
    )

    from core import app as core_app

    class FakeGoalManager:
        def get_active_goal(self):
            return {"id": "goal-1", "title": "objectif actif", "status": "active"}

    class FakeSelfModel:
        def refresh(self):
            return None

        def to_dict(self):
            return {
                "identity": {"name": "Néron"},
                "active_goal": "objectif actif",
                "runtime": {},
                "diagnostics": [],
                "recommendations": [],
            }

    class FakeTaskManager:
        def list_tasks(self):
            return []

        def list_active_tasks(self):
            return []

    monkeypatch.setattr(goal_routes, "get_goal_manager", lambda: FakeGoalManager())
    monkeypatch.setattr(self_model_context_routes, "get_self_model", lambda: FakeSelfModel())
    monkeypatch.setattr(self_model_context_routes, "get_task_manager", lambda: FakeTaskManager())
    monkeypatch.setattr(self_model_context_routes, "scan_project", lambda max_depth=1: {"modules": 0, "files": 0})

    assert core_app.health()["status"] == "healthy"
    assert (await goal_routes.active_goal())["active_goal"]["id"] == "goal-1"
    context = await self_model_context_routes.self_model_context()
    assert context["identity"]["name"] == "Néron"
