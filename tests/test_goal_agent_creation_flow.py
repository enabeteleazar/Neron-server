from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from core.cognitive import critic_engine
from core.goals import goal_manager, persistence
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
    executor = PlanExecutor(project_root=project_root)
    orchestrator = GoalOrchestrator(storage=storage, notifier=notifier)
    orchestrator.storage = storage
    orchestrator.task_manager = TaskManager()
    orchestrator.task_executor = TaskExecutor(plan_executor=executor, storage=storage)
    return orchestrator


def test_goal_agent_creation_generates_draft_and_report(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        notifications: list[tuple[str, str]] = []
        orchestrator = _build_orchestrator(tmp_path, monkeypatch, notifications)

        result = asyncio.run(
            orchestrator.run_goal("créer un agent de test automatique", source="telegram")
        )

        assert result["status"] == "plan_finished"
        plan = result["plan"]
        agent_path = Path(plan["agent_path"])
        assert agent_path.exists()
        assert agent_path.parent == tmp_path / "project" / "workspace" / "agent_drafts"
        assert "status': 'draft_only'" in agent_path.read_text(encoding="utf-8")

        tasks = orchestrator.task_manager.list_tasks()
        create_skeleton = next(task for task in tasks if task.get("action") == "create_skeleton")
        assert create_skeleton["status"] == "completed"
        assert create_skeleton["result"]["agent_path"] == str(agent_path)

        final_report = notifications[-1][0]
        assert "Agent :" in final_report
        assert str(agent_path) in final_report
        assert "Statut final :\nplan_finished" in final_report


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
        assert not result["plan"].get("agent_path")
        assert "Aucune tâche exécutable" in result["plan"]["error"]
