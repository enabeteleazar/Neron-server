from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import httpx
from fastapi import FastAPI

from goal.goals.execution_engine import GoalExecutionEngine
from modules.scheduler.scheduler import TaskScheduler
from modules.scheduler.store import SchedulerStore
from core.storage.sqlite_store import SQLiteStore
from tools.creator import LOG_TOOL_SLUGS, ToolCreator
from tools.models import ToolResult, ToolSpec
from tools.registry import ToolRegistry
from tools.runtime import ToolRuntime


LOGS = [
    "INFO api started",
    "ERROR core failed",
    "CRITICAL planner timeout",
]


def make_scheduler(tmp_path: Path) -> tuple[TaskScheduler, ToolCreator]:
    registry = ToolRegistry(tmp_path / "tools.json")
    creator = ToolCreator(registry=registry)
    creator.ensure_tools_for_request("Analyse les logs Néron")
    scheduler = TaskScheduler(
        store=SchedulerStore(tmp_path / "scheduler.sqlite3"),
        tool_runtime=creator.runtime,
    )
    return scheduler, creator


def test_enqueue_simple_task(tmp_path: Path):
    scheduler, _ = make_scheduler(tmp_path)

    task = scheduler.enqueue_task(
        title="Lire les logs",
        kind="tool_execution",
        payload={"tool_slug": "neron_log_reader_tool", "logs": LOGS},
    )

    assert task.status == "queued"
    assert scheduler.get_task(task.task_id) == task


async def test_run_simple_task(tmp_path: Path):
    scheduler, _ = make_scheduler(tmp_path)
    task = scheduler.enqueue_task(
        title="Lire les logs",
        kind="tool_execution",
        payload={"tool_slug": "neron_log_reader_tool", "logs": LOGS},
    )

    completed = await scheduler.run_task(task.task_id)

    assert completed is not None
    assert completed.status == "completed"
    assert completed.result["data"]["line_count"] == 3
    assert completed.started_at
    assert completed.finished_at


def test_scheduler_tasks_persist_in_sqlite(tmp_path: Path):
    database = tmp_path / "scheduler.sqlite3"
    scheduler = TaskScheduler(store=SchedulerStore(database))
    created = scheduler.enqueue_task(
        title="Persisted task",
        kind="notification",
        payload={"message": "hello"},
    )

    reloaded = TaskScheduler(store=SchedulerStore(database)).get_task(created.task_id)

    assert reloaded == created
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT status FROM scheduler_tasks WHERE task_id = ?",
            (created.task_id,),
        ).fetchone()
    assert row == ("queued",)


async def test_dependency_waits_for_previous_task(tmp_path: Path):
    scheduler, _ = make_scheduler(tmp_path)
    first = scheduler.enqueue_task(
        title="First",
        kind="notification",
        payload={"message": "first"},
    )
    second = scheduler.enqueue_task(
        title="Second",
        kind="notification",
        payload={"message": "second"},
        depends_on=[first.task_id],
    )

    waiting = await scheduler.run_task(second.task_id)
    assert waiting.status == "queued"

    await scheduler.run_task(first.task_id)
    completed = await scheduler.run_task(second.task_id)
    assert completed.status == "completed"


async def test_failed_dependency_blocks_dependent_task(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")
    registry.register_tool(
        ToolSpec(
            name="Failing tool",
            slug="failing_tool",
            description="Always fails",
            safety={"allow_system_commands": False},
        )
    )
    runtime = ToolRuntime(
        registry,
        handlers={
            "failing_tool": lambda _payload: ToolResult(
                ok=False,
                error="expected failure",
            )
        },
    )
    scheduler = TaskScheduler(
        store=SchedulerStore(tmp_path / "scheduler.sqlite3"),
        tool_runtime=runtime,
    )
    first = scheduler.enqueue_task(
        title="Fail",
        kind="tool_execution",
        payload={"tool_slug": "failing_tool"},
    )
    second = scheduler.enqueue_task(
        title="Blocked",
        kind="notification",
        payload={"message": "never"},
        depends_on=[first.task_id],
    )

    failed = await scheduler.run_task(first.task_id)
    blocked = await scheduler.run_task(second.task_id)

    assert failed.status == "failed"
    assert blocked.status == "blocked"
    assert first.task_id in blocked.error


def test_cancel_task(tmp_path: Path):
    scheduler, _ = make_scheduler(tmp_path)
    task = scheduler.enqueue_task(title="Cancel me", kind="notification")

    cancelled = scheduler.cancel_task(task.task_id)

    assert cancelled.status == "cancelled"
    assert cancelled.finished_at


async def test_high_priority_runs_before_low_priority(tmp_path: Path):
    scheduler, _ = make_scheduler(tmp_path)
    low = scheduler.enqueue_task(
        title="Low",
        kind="notification",
        priority="low",
        payload={"message": "low"},
    )
    high = scheduler.enqueue_task(
        title="High",
        kind="notification",
        priority="high",
        payload={"message": "high"},
    )

    completed = await scheduler.run_next()

    assert completed.task_id == high.task_id
    assert scheduler.get_task(low.task_id).status == "queued"


async def test_retry_requeues_then_completes(tmp_path: Path):
    attempts = 0
    registry = ToolRegistry(tmp_path / "tools.json")
    registry.register_tool(
        ToolSpec(
            name="Flaky tool",
            slug="flaky_tool",
            description="Fails once",
            safety={"allow_system_commands": False},
        )
    )

    def flaky(_payload):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return ToolResult(ok=False, error="temporary failure")
        return ToolResult(ok=True, data={"attempts": attempts})

    scheduler = TaskScheduler(
        store=SchedulerStore(tmp_path / "scheduler.sqlite3"),
        tool_runtime=ToolRuntime(registry, handlers={"flaky_tool": flaky}),
    )
    task = scheduler.enqueue_task(
        title="Retry",
        kind="tool_execution",
        payload={"tool_slug": "flaky_tool"},
        max_retries=1,
    )

    retried = await scheduler.run_task(task.task_id)
    completed = await scheduler.run_task(task.task_id)

    assert retried.status == "queued"
    assert retried.retry_count == 1
    assert completed.status == "completed"
    assert completed.result["data"]["attempts"] == 2


async def test_max_retries_reached_marks_failed(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")
    registry.register_tool(
        ToolSpec(
            name="Failing tool",
            slug="always_fails",
            description="Always fails",
            safety={"allow_system_commands": False},
        )
    )
    runtime = ToolRuntime(
        registry,
        handlers={
            "always_fails": lambda _payload: ToolResult(
                ok=False,
                error="temporary failure",
            )
        },
    )
    scheduler = TaskScheduler(
        store=SchedulerStore(tmp_path / "scheduler.sqlite3"),
        tool_runtime=runtime,
    )
    task = scheduler.enqueue_task(
        title="Retry exhausted",
        kind="tool_execution",
        payload={"tool_slug": "always_fails"},
        max_retries=1,
    )

    await scheduler.run_task(task.task_id)
    failed = await scheduler.run_task(task.task_id)

    assert failed.status == "failed"
    assert failed.retry_count == 1
    assert failed.error == "temporary failure"


def test_recovery_marks_running_task_interrupted(tmp_path: Path):
    scheduler, _ = make_scheduler(tmp_path)
    task = scheduler.enqueue_task(title="Running", kind="notification")
    task.status = "running"
    task.started_at = task.created_at
    scheduler.store.save_task(task)

    recovered = TaskScheduler(
        store=SchedulerStore(tmp_path / "scheduler.sqlite3")
    ).recover_running_tasks()

    assert [item.task_id for item in recovered] == [task.task_id]
    restored = scheduler.get_task(task.task_id)
    assert restored.status == "interrupted"
    assert restored.metadata["recovery_reason"] == "scheduler_restarted"
    assert restored.finished_at


async def test_continuous_worker_executes_queued_task(tmp_path: Path):
    scheduler, _ = make_scheduler(tmp_path)
    scheduler.worker_enabled = True
    scheduler.worker_poll_interval = 0.01
    task = scheduler.enqueue_task(
        title="Worker task",
        kind="notification",
        payload={"message": "done"},
    )

    try:
        assert await scheduler.start_worker() is True
        for _ in range(100):
            if scheduler.get_task(task.task_id).status == "completed":
                break
            await asyncio.sleep(0.01)
    finally:
        await scheduler.stop_worker()

    assert scheduler.get_task(task.task_id).status == "completed"


async def test_worker_respects_max_concurrent_tasks(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")
    registry.register_tool(
        ToolSpec(
            name="Blocking tool",
            slug="blocking_tool",
            description="Blocks until released",
            safety={"allow_system_commands": False},
        )
    )
    release = asyncio.Event()
    running = 0
    peak = 0

    async def blocking(_payload):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await release.wait()
        running -= 1
        return ToolResult(ok=True)

    scheduler = TaskScheduler(
        store=SchedulerStore(tmp_path / "scheduler.sqlite3"),
        tool_runtime=ToolRuntime(
            registry,
            handlers={"blocking_tool": blocking},
        ),
        worker_enabled=True,
        max_concurrent_tasks=2,
    )
    for index in range(3):
        scheduler.enqueue_task(
            title=f"Blocking {index}",
            kind="tool_execution",
            payload={"tool_slug": "blocking_tool"},
        )

    launched = await scheduler.run_worker_once(wait=False)
    await asyncio.sleep(0)
    assert launched == 2
    assert peak == 2

    release.set()
    await asyncio.gather(*list(scheduler._active_tasks))
    await scheduler.run_worker_once()
    assert peak == 2


async def test_complete_log_tool_chain(tmp_path: Path):
    scheduler, _ = make_scheduler(tmp_path)
    tasks = scheduler.enqueue_tool_chain(
        list(LOG_TOOL_SLUGS),
        initial_payload={"logs": LOGS},
        title="Analyse logs",
    )

    for _ in tasks:
        completed = await scheduler.run_next()
        assert completed is not None
        assert completed.status == "completed"

    final = scheduler.get_task(tasks[-1].task_id)
    data = final.result["data"]
    assert data["error_count"] == 2
    assert data["severity"] == "critical"
    assert set(data["components"]) >= {"core", "planner"}
    assert data["excerpt"]
    assert data["recommendation"]


async def test_log_chain_composite_exposes_final_summary(tmp_path: Path):
    scheduler, _ = make_scheduler(tmp_path)
    tasks = scheduler.enqueue_tool_chain(
        list(LOG_TOOL_SLUGS),
        initial_payload={"logs": LOGS},
        title="Analyse logs",
    )
    composite = scheduler.enqueue_composite_task(
        title="Log result",
        depends_on=[tasks[-1].task_id],
    )

    for _ in range(4):
        await scheduler.run_next()

    result = scheduler.get_task(composite.task_id).result["data"]
    assert result["error_count"] == 2
    assert result["severity"] == "critical"
    assert result["recommendation"]


async def test_scheduler_calls_tool_runtime_with_dependency_data(tmp_path: Path):
    calls: list[tuple[str, dict]] = []
    registry = ToolRegistry(tmp_path / "tools.json")
    for slug in ("producer_tool", "consumer_tool"):
        registry.register_tool(
            ToolSpec(
                name=slug,
                slug=slug,
                description=slug,
                safety={"allow_system_commands": False},
            )
        )

    def producer(payload):
        calls.append(("producer_tool", payload))
        return ToolResult(ok=True, data={"value": 42})

    def consumer(payload):
        calls.append(("consumer_tool", payload))
        return ToolResult(ok=True, data={"received": payload["value"]})

    runtime = ToolRuntime(
        registry,
        handlers={"producer_tool": producer, "consumer_tool": consumer},
    )
    scheduler = TaskScheduler(
        store=SchedulerStore(tmp_path / "scheduler.sqlite3"),
        tool_runtime=runtime,
    )
    tasks = scheduler.enqueue_tool_chain(["producer_tool", "consumer_tool"])

    await scheduler.run_task(tasks[0].task_id)
    await scheduler.run_task(tasks[1].task_id)

    assert calls[1][1]["value"] == 42
    assert scheduler.get_task(tasks[1].task_id).result["data"]["received"] == 42


async def test_task_scheduler_endpoints(tmp_path: Path, monkeypatch):
    from core.scheduler import routes

    scheduler, _ = make_scheduler(tmp_path)
    task = scheduler.enqueue_task(
        title="Endpoint task",
        kind="notification",
        payload={"message": "done"},
    )
    monkeypatch.setattr(routes, "get_task_scheduler", lambda: scheduler)
    app = FastAPI()
    app.include_router(routes.router)

    async def allow_request():
        return None

    app.dependency_overrides[routes.verify_api_key] = allow_request
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        listed = await client.get("/tasks")
        fetched = await client.get(f"/tasks/{task.task_id}")
        status = await client.get("/tasks/status")
        ran = await client.post(f"/tasks/{task.task_id}/run")

    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert fetched.json()["task_id"] == task.task_id
    assert status.json() == {
        "queued_count": 1,
        "running_count": 0,
        "completed_count": 0,
        "failed_count": 0,
        "worker_enabled": False,
        "max_concurrent_tasks": 2,
    }
    assert ran.json()["status"] == "completed"


def test_goal_engine_remains_compatible_with_scheduler_table(tmp_path: Path):
    store = SQLiteStore(tmp_path / "shared.sqlite3")
    engine = GoalExecutionEngine(store)
    engine.enqueue_goal("goal-scheduler-compat", "Compatibility", "test", {})

    assert engine.get_goal_status("goal-scheduler-compat")["status"] == "queued"
    with sqlite3.connect(store.path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"goal_runs", "scheduler_tasks"}.issubset(tables)
