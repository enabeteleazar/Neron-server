from __future__ import annotations

import json

import pytest

from core.storage.sqlite_store import SQLiteStore


def test_task_manager_imports_json_once_then_reads_sqlite(monkeypatch, tmp_path):
    from core.task_system import task_manager

    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": "task-legacy",
                        "title": "Legacy task",
                        "description": "",
                        "priority": "medium",
                        "status": "active",
                        "source": "legacy",
                        "metadata": {},
                        "progress": 0,
                        "created_at": "2026-01-01T00:00:00+00:00",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                        "completed_at": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    store = SQLiteStore(tmp_path / "neron_state.sqlite3")

    manager = task_manager.TaskManager(path=tasks_path, sqlite_store=store)
    assert manager.get_task("task-legacy") is not None

    tasks_path.write_text(json.dumps({"tasks": []}), encoding="utf-8")
    reloaded = task_manager.TaskManager(path=tasks_path, sqlite_store=store)

    assert reloaded.get_task("task-legacy") is not None


def test_concurrent_task_managers_do_not_erase_new_tasks(tmp_path):
    from core.task_system.task_manager import TaskManager

    store = SQLiteStore(tmp_path / "neron_state.sqlite3")
    first = TaskManager(path=tmp_path / "tasks.json", sqlite_store=store)
    second = TaskManager(path=tmp_path / "tasks.json", sqlite_store=store)

    first_task = first.create_task("First")
    second_task = second.create_task("Second")

    reloaded = TaskManager(path=tmp_path / "tasks.json", sqlite_store=store)
    assert reloaded.get_task(first_task["id"]) is not None
    assert reloaded.get_task(second_task["id"]) is not None


def test_workflow_owners_emit_canonical_created_events(monkeypatch, tmp_path):
    from core.goals import goal_manager, persistence
    from core.planning import storage as plan_storage
    from core.projects import manager as project_manager
    from core.task_system import task_manager

    emitted = []
    monkeypatch.setattr(persistence, "GOALS_PATH", tmp_path / "goals_state.json")
    for module in (goal_manager, plan_storage, project_manager, task_manager):
        monkeypatch.setattr(module.event_bus, "publish_background", emitted.append)

    store = SQLiteStore(tmp_path / "neron_state.sqlite3")
    goals = goal_manager.GoalManager(sqlite_store=store)
    goal = goals.create_goal("Audit workflow", deduplicate=False)

    plans = plan_storage.PlanStorage(
        tmp_path / "plans.jsonl",
        sqlite_store=store,
    )
    plans.save(
        {
            "id": "plan-1",
            "goal_id": goal["id"],
            "goal": goal["title"],
            "status": "pending",
            "steps": [],
        }
    )

    tasks = task_manager.TaskManager(
        path=tmp_path / "tasks.json",
        sqlite_store=store,
    )
    tasks.create_task(
        "Execute audit",
        goal_id=goal["id"],
        plan_id="plan-1",
    )

    projects = project_manager.ProjectManager(
        tmp_path / "projects.json",
        sqlite_store=store,
    )
    projects.create_project(
        title="Audit workflow",
        project_type="agent",
        metadata={"goal_id": goal["id"], "plan_id": "plan-1"},
    )

    assert [event.type for event in emitted] == [
        "goal.created",
        "plan.created",
        "task.created",
        "project.created",
    ]


@pytest.mark.asyncio
async def test_agent_build_owner_emits_agent_created(monkeypatch, tmp_path):
    from core.agent_factory import build_orchestrator

    emitted = []

    async def capture(event):
        emitted.append(event)

    monkeypatch.setattr(build_orchestrator.event_bus, "publish", capture)
    orchestrator = build_orchestrator.AgentBuildOrchestrator(
        project_root=tmp_path,
    )

    await orchestrator._publish_agent_created(
        agent_slug="audit_agent",
        project_id="project-1",
        metadata={"goal_id": "goal-1", "plan_id": "plan-1"},
        destination=tmp_path / "audit_agent.py",
        runtime_status="available",
    )

    assert emitted[0].type == "agent.created"
    assert emitted[0].payload["agent_slug"] == "audit_agent"
