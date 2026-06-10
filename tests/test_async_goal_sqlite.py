from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from core.goals import goal_manager, goal_orchestrator, persistence, routes
from core.goals.background_runner import GoalBackgroundRunner
from core.goals.goal_orchestrator import GoalOrchestrator
from core.planning.storage import PlanStorage
from core.projects.manager import ProjectManager
from core.storage.sqlite_store import SQLiteStore


def build_state(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(persistence, "GOALS_PATH", data_dir / "goals_state.json")
    monkeypatch.setattr(goal_manager, "_GOAL_MANAGER", None)
    manager = goal_manager.get_goal_manager()
    storage = PlanStorage(data_dir / "plans.jsonl")
    projects = ProjectManager(data_dir / "projects.json")

    orchestrator = GoalOrchestrator.__new__(GoalOrchestrator)
    orchestrator.goal_manager = manager
    orchestrator.storage = storage
    orchestrator.agent_build_orchestrator = SimpleNamespace(
        project_manager=projects
    )
    return manager, storage, projects, orchestrator


def test_sqlite_store_uses_wal_and_idempotent_migrations(tmp_path: Path):
    database = tmp_path / "data" / "neron_state.sqlite3"
    store = SQLiteStore(database)
    store.migrate()

    assert store.journal_mode() == "wal"
    assert store.busy_timeout() == 5000
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {
        "goals",
        "projects",
        "workflows",
        "workflow_steps",
        "test_results",
    }.issubset(tables)


@pytest.mark.asyncio
async def test_post_goal_returns_202_immediately_and_status_is_queued(
    tmp_path: Path,
    monkeypatch,
):
    _, _, _, orchestrator = build_state(tmp_path, monkeypatch)

    class RecordingRunner:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def submit(self, **kwargs) -> None:
            self.calls.append(kwargs)

    runner = RecordingRunner()
    monkeypatch.setattr(routes, "get_goal_orchestrator", lambda: orchestrator)
    monkeypatch.setattr(routes, "get_goal_background_runner", lambda: runner)

    app = FastAPI()
    app.include_router(routes.router)
    transport = httpx.ASGITransport(app=app)
    started = time.monotonic()
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/goal",
            json={"goal": "Créer un agent asynchrone", "source": "api"},
        )
        elapsed = time.monotonic() - started
        payload = response.json()
        status_response = await client.get(payload["status_url"])

    assert response.status_code == 202
    assert elapsed < 0.5
    assert payload == {
        "accepted": True,
        "goal_id": payload["goal_id"],
        "status": "queued",
        "status_url": f"/goal/{payload['goal_id']}/status",
    }
    assert runner.calls == [
        {
            "goal_id": payload["goal_id"],
            "objective": "Créer un agent asynchrone",
            "source": "api",
        }
    ]
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "queued"
    assert status_response.json()["current_step"] == "queued"
    assert status_response.json()["progress"] == 0


@pytest.mark.asyncio
async def test_background_completed_workflow_remains_observable(
    tmp_path: Path,
    monkeypatch,
):
    manager, _, _, observer = build_state(tmp_path, monkeypatch)
    goal = observer.queue_goal("Objectif terminé en arrière-plan", source="api")

    class CompletingOrchestrator:
        async def run_goal(self, objective, source="system", goal_id=None):
            manager.update_progress(goal_id, 1.0)
            manager.update_status(
                goal_id,
                "completed",
                current_step="completed",
            )
            return {"status": "completed"}

    monkeypatch.setattr(
        goal_orchestrator,
        "get_goal_orchestrator",
        lambda: CompletingOrchestrator(),
    )
    runner = GoalBackgroundRunner()
    runner.submit(
        goal_id=goal["id"],
        objective=goal["title"],
        source="api",
    )
    await runner.wait(goal["id"], timeout=2)

    status = observer.get_goal_status(goal["id"])
    assert status is not None
    assert status["status"] == "completed"
    assert status["current_step"] == "completed"
    assert status["progress"] == 100
    assert status["error"] is None


@pytest.mark.asyncio
async def test_background_workflow_exception_becomes_failed(
    tmp_path: Path,
    monkeypatch,
):
    _, _, _, observer = build_state(tmp_path, monkeypatch)
    goal = observer.queue_goal("Objectif en erreur", source="api")

    class FailingOrchestrator:
        async def run_goal(self, objective, source="system", goal_id=None):
            raise RuntimeError("workflow exploded")

    monkeypatch.setattr(
        goal_orchestrator,
        "get_goal_orchestrator",
        lambda: FailingOrchestrator(),
    )
    runner = GoalBackgroundRunner()
    runner.submit(
        goal_id=goal["id"],
        objective=goal["title"],
        source="api",
    )
    await runner.wait(goal["id"], timeout=2)

    status = observer.get_goal_status(goal["id"])
    assert status is not None
    assert status["status"] == "failed"
    assert status["current_step"] == "failed"
    assert status["error"] == "workflow exploded"


@pytest.mark.asyncio
async def test_two_parallel_goals_do_not_corrupt_sqlite_or_legacy_state(
    tmp_path: Path,
    monkeypatch,
):
    manager, storage, projects, observer = build_state(tmp_path, monkeypatch)
    first = observer.queue_goal("Premier objectif parallèle", source="api")
    second = observer.queue_goal("Second objectif parallèle", source="api")

    class ConcurrentOrchestrator:
        async def run_goal(self, objective, source="system", goal_id=None):
            await asyncio.sleep(0.02)
            plan_id = f"plan-{goal_id}"
            storage.save(
                {
                    "id": plan_id,
                    "goal_id": goal_id,
                    "goal": objective,
                    "status": "running",
                    "current_step": "planning",
                    "steps": [{"name": "planning", "status": "completed"}],
                }
            )
            project = projects.create_project(
                title=objective,
                project_type="agent",
                metadata={"goal_id": goal_id, "plan_id": plan_id},
            )
            projects.update_project(
                project["project_id"],
                {
                    "status": "completed",
                    "runtime_status": "available",
                    "test_results": [
                        {
                            "name": "pytest_agent",
                            "returncode": 0,
                            "ran_at": "2026-06-10T00:00:00+00:00",
                        }
                    ],
                },
                step="verification",
                step_status="done",
                progress=100,
            )
            manager.update_progress(goal_id, 1.0)
            manager.update_status(
                goal_id,
                "completed",
                current_step="completed",
            )
            return {"status": "completed"}

    monkeypatch.setattr(
        goal_orchestrator,
        "get_goal_orchestrator",
        lambda: ConcurrentOrchestrator(),
    )
    runner = GoalBackgroundRunner()
    runner.submit(goal_id=first["id"], objective=first["title"], source="api")
    runner.submit(goal_id=second["id"], objective=second["title"], source="api")
    await asyncio.gather(
        runner.wait(first["id"], timeout=2),
        runner.wait(second["id"], timeout=2),
    )

    stored = {goal["id"]: goal for goal in manager.sqlite_store.list_goals()}
    assert stored[first["id"]]["status"] == "completed"
    assert stored[second["id"]]["status"] == "completed"
    assert len(storage.sqlite_store.list_workflows()) == 2
    assert len(projects.sqlite_store.list_projects()) == 2
    with sqlite3.connect(manager.sqlite_store.path) as connection:
        workflow_step_count = connection.execute(
            "SELECT COUNT(*) FROM workflow_steps"
        ).fetchone()[0]
        test_result_count = connection.execute(
            "SELECT COUNT(*) FROM test_results"
        ).fetchone()[0]
    assert workflow_step_count == 4
    assert test_result_count == 2

    legacy = json.loads(persistence.GOALS_PATH.read_text(encoding="utf-8"))
    legacy_by_id = {goal["id"]: goal for goal in legacy["goals"]}
    assert legacy_by_id[first["id"]]["status"] == "completed"
    assert legacy_by_id[second["id"]]["status"] == "completed"
    assert len(json.loads(projects.path.read_text(encoding="utf-8"))["projects"]) == 2
    assert len(storage.path.read_text(encoding="utf-8").splitlines()) == 2


def test_project_manager_imports_legacy_json_into_sqlite(tmp_path: Path):
    data_dir = tmp_path / "data"
    projects_path = data_dir / "projects.json"
    projects_path.parent.mkdir(parents=True)
    legacy_project = {
        "project_id": "legacy-project",
        "title": "Legacy",
        "type": "agent",
        "status": "completed",
        "current_step": "completed",
        "progress": 100,
        "created_at": 1.0,
        "updated_at": 2.0,
        "steps": [],
        "test_results": [],
        "metadata": {"goal_id": "legacy-goal"},
    }
    projects_path.write_text(
        json.dumps({"projects": [legacy_project]}),
        encoding="utf-8",
    )

    manager = ProjectManager(projects_path)

    assert manager.get_project("legacy-project") == legacy_project
    assert manager.sqlite_store.get_project("legacy-project") == legacy_project


def test_partial_legacy_import_adds_missing_rows_without_overwriting_sqlite(
    tmp_path: Path,
):
    data_dir = tmp_path / "data"
    projects_path = data_dir / "projects.json"
    store = SQLiteStore(data_dir / "neron_state.sqlite3")
    sqlite_project = {
        "project_id": "existing-project",
        "title": "SQLite current",
        "type": "agent",
        "status": "running",
        "current_step": "tests",
        "progress": 70,
        "created_at": 1.0,
        "updated_at": 3.0,
        "steps": [],
        "test_results": [],
        "metadata": {},
    }
    missing_legacy_project = {
        **sqlite_project,
        "project_id": "missing-project",
        "title": "Legacy missing",
        "updated_at": 2.0,
    }
    store.upsert_project(sqlite_project)
    projects_path.write_text(
        json.dumps(
            {
                "projects": [
                    {**sqlite_project, "title": "stale legacy"},
                    missing_legacy_project,
                ]
            }
        ),
        encoding="utf-8",
    )

    manager = ProjectManager(projects_path)

    assert manager.get_project("existing-project")["title"] == "SQLite current"
    assert manager.get_project("missing-project") == missing_legacy_project
