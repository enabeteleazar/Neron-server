from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from core.agent_factory.agent_creator import AgentCreator
from core.agent_factory.build_orchestrator import AgentBuildOrchestrator
from core.cognitive import critic_engine
from core.goals import goal_manager, persistence, routes as goal_routes
from core.goals.goal_orchestrator import GoalOrchestrator
from core.planning.executor import PlanExecutor
from core.planning.storage import PlanStorage
from core.projects.manager import ProjectManager
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
    orchestrator.agent_build_orchestrator = AgentBuildOrchestrator(
        project_manager=ProjectManager(data_dir / "projects.json"),
        project_root=project_root,
        workspace_agents=project_root / "workspace" / "agents",
        workspace_tests=project_root / "workspace" / "agent_tests",
        generated_agents=project_root / "core" / "agents" / "generated",
        runtime_check=False,
    )
    orchestrator.task_executor = TaskExecutor(
        plan_executor=executor,
        storage=storage,
        agent_creator=agent_creator,
    )
    return orchestrator


def test_goal_creates_specialized_agent_without_human_approval(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        notifications: list[tuple[str, str]] = []
        orchestrator = _build_orchestrator(tmp_path, monkeypatch, notifications)

        result = asyncio.run(
            orchestrator.run_goal(
                "Créer un agent météo spécialisé agriculture",
                source="api",
            )
        )

        assert result["status"] == "plan_finished"
        assert result["goal_id"]
        assert result["planner_called"] is True
        assert result["plan_id"]
        assert result["plan"]["steps"]
        assert result["agent_creator_called"] is True
        assert result["plan"]["approval_required"] is False
        assert result["plan"]["human_validation_required"] is False
        assert result["plan"]["agent_name"] == "agriculture_weather_agent"
        assert result["plan"]["registered_agent"] == "agriculture_weather_agent"
        assert result["plan"]["agent_path"] == "core/agents/generated/agriculture_weather_agent.py"
        assert result["plan"]["agent_state"] == "registered"
        assert result["plan"]["registry_status"] == "registered"
        assert result["plan"]["tests_ok"] is True
        assert result["plan"]["runtime_reload"]["ok"] is True
        assert "agriculture_weather_agent" in result["plan"]["runtime_reload"]["agents"]
        assert result["plan"]["execution_summary"] == {
            "completed": 4,
            "skipped": 0,
            "failed": 0,
            "total": 4,
        }

        proposal = result["proposal"]
        assert proposal["agent_name"] == "agriculture_weather_agent"
        assert proposal["required_capabilities"] == [
            "parse_agriculture_weather_request",
            "static_agriculture_weather_fallback",
            "format_agriculture_weather_response",
        ]
        assert proposal["status"] == "auto_applied"
        assert proposal["created_from_goal_id"] == result["goal_id"]
        assert proposal["created_from_plan_id"] == result["plan_id"]
        assert proposal["human_validation_required"] is False
        assert proposal["code_execution_allowed"] is True
        assert proposal["applied_to_core"] is True

        agent_path = tmp_path / "project" / "core" / "agents" / "generated" / "agriculture_weather_agent.py"
        workspace_path = tmp_path / "project" / "workspace" / "agents" / "agriculture_weather_agent.py"
        assert agent_path.exists()
        assert workspace_path.exists()
        generated = agent_path.read_text(encoding="utf-8")
        assert "parse_agriculture_weather_request" in generated
        assert "Spécialisation agriculture" in generated
        assert not (tmp_path / "project" / "workspace" / "agent_drafts" / "agriculture_weather_agent.py").exists()

        final_report = notifications[-1][0]
        assert "🏁 Objectif terminé" in final_report
        assert "completed : 4" in final_report
        assert "skipped : 0" in final_report
        assert "failed : 0" in final_report
        assert "core/agents/generated/agriculture_weather_agent.py" in final_report


def test_sensitive_agent_creation_goal_is_blocked_before_build(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        notifications: list[tuple[str, str]] = []
        orchestrator = _build_orchestrator(tmp_path, monkeypatch, notifications)

        result = asyncio.run(
            orchestrator.run_goal(
                "Créer un agent pour modifier systemd et lire les secrets",
                source="api",
            )
        )

        assert result["status"] == "blocked"
        assert result["plan"]["status"] == "blocked_by_risk"
        assert result["plan"]["risk"]["sensitive_action_detected"] is True
        assert result["plan"]["approval_required"] is False
        assert not (tmp_path / "project" / "workspace" / "agents").exists()
        assert not (tmp_path / "project" / "core" / "agents" / "generated").exists()


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

        def collect_runtime(self):
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
    assert (await self_model_context_routes.self_model_status())["diagnostics"] == []
    assert (await goal_routes.active_goal())["active_goal"]["id"] == "goal-1"
    context = await self_model_context_routes.self_model_context()
    assert context["identity"]["name"] == "Néron"
