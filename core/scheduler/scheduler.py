from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4

from core.scheduler.models import ScheduledTask, utc_now_iso
from core.scheduler.store import SchedulerStore
from core.tools.runtime import ToolRuntime, get_tool_runtime


PRIORITY_WEIGHT = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

Notifier = Callable[[str], Awaitable[None] | None]


class TaskScheduler:
    def __init__(
        self,
        *,
        store: SchedulerStore | None = None,
        tool_runtime: ToolRuntime | None = None,
        agent_runtime: Any | None = None,
        goal_orchestrator: Any | None = None,
        notifier: Notifier | None = None,
        worker_enabled: bool | None = None,
        max_concurrent_tasks: int | None = None,
        worker_poll_interval: float | None = None,
    ) -> None:
        self.store = store or SchedulerStore()
        self.tool_runtime = tool_runtime or get_tool_runtime()
        self._agent_runtime = agent_runtime
        self._goal_orchestrator = goal_orchestrator
        self.notifier = notifier
        self.worker_enabled = (
            _env_bool("NERON_TASK_WORKER_ENABLED", False)
            if worker_enabled is None
            else bool(worker_enabled)
        )
        self.max_concurrent_tasks = max(
            1,
            int(
                max_concurrent_tasks
                if max_concurrent_tasks is not None
                else os.getenv("NERON_TASK_MAX_CONCURRENT", "2")
            ),
        )
        self.worker_poll_interval = max(
            0.01,
            float(
                worker_poll_interval
                if worker_poll_interval is not None
                else os.getenv("NERON_TASK_WORKER_POLL_SECONDS", "0.25")
            ),
        )
        self._worker_task: asyncio.Task[None] | None = None
        self._active_tasks: set[asyncio.Task[ScheduledTask | None]] = set()
        self._wake_event: asyncio.Event | None = None

    def enqueue_task(
        self,
        *,
        title: str,
        kind: str,
        priority: str = "medium",
        payload: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        max_retries: int = 0,
        retry_delay_seconds: float = 0.0,
    ) -> ScheduledTask:
        task = ScheduledTask(
            title=title,
            kind=kind,
            priority=priority,
            payload=dict(payload or {}),
            depends_on=list(depends_on or []),
            metadata=dict(metadata or {}),
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
        )
        saved = self.store.save_task(task)
        self.wake_worker()
        return saved

    def get_task(self, task_id: str) -> ScheduledTask | None:
        return self.store.get_task(task_id)

    def list_tasks(
        self,
        *,
        status: str | None = None,
        kind: str | None = None,
    ) -> list[ScheduledTask]:
        return self.store.list_tasks(status=status, kind=kind)

    async def run_task(self, task_id: str) -> ScheduledTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        if task.status in {"completed", "failed", "cancelled", "interrupted"}:
            return task
        if not self._retry_is_ready(task):
            return task

        dependencies = self.resolve_dependencies(task_id)
        if dependencies["failed"]:
            return self._mark_blocked(
                task,
                f"dependency_failed: {', '.join(dependencies['failed'])}",
            )
        if dependencies["pending"]:
            return task

        task.status = "running"
        task.started_at = task.started_at or utc_now_iso()
        task.updated_at = utc_now_iso()
        task.error = None
        self.store.save_task(task)

        payload = self._payload_with_dependency_results(task)
        try:
            result = await self._execute(task, payload)
        except Exception as exc:
            return self._retry_or_fail(task, str(exc))

        if result.get("ok") is False:
            return self._retry_or_fail(
                task,
                str(result.get("error") or "task_execution_failed"),
                result=result,
            )
        return self.mark_completed(task.task_id, result)

    async def run_next(self) -> ScheduledTask | None:
        ready = self._ready_tasks()
        if not ready:
            return None
        return await self.run_task(ready[0].task_id)

    async def start_worker(self) -> bool:
        if not self.worker_enabled:
            return False
        if self._worker_task is not None and not self._worker_task.done():
            return True
        self._wake_event = asyncio.Event()
        self._worker_task = asyncio.create_task(
            self._worker_loop(),
            name="neron-task-scheduler-worker",
        )
        return True

    async def stop_worker(self) -> None:
        self.worker_enabled = False
        self.wake_worker()
        if self._worker_task is not None:
            self._worker_task.cancel()
            await asyncio.gather(self._worker_task, return_exceptions=True)
            self._worker_task = None
        active = list(self._active_tasks)
        for task in active:
            task.cancel()
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        self._active_tasks.clear()

    async def run_worker_once(self, *, wait: bool = True) -> int:
        self._discard_finished_worker_tasks()
        available = self.max_concurrent_tasks - len(self._active_tasks)
        if available <= 0:
            return 0
        ready = self._ready_tasks()[:available]
        launched = [
            asyncio.create_task(
                self.run_task(task.task_id),
                name=f"scheduler-task-{task.task_id}",
            )
            for task in ready
        ]
        self._active_tasks.update(launched)
        if wait and launched:
            await asyncio.gather(*launched)
            self._discard_finished_worker_tasks()
        return len(launched)

    def recover_running_tasks(self) -> list[ScheduledTask]:
        return self.store.recover_running_tasks()

    def status(self) -> dict[str, Any]:
        counts = {
            status: len(self.list_tasks(status=status))
            for status in ("queued", "running", "completed", "failed")
        }
        return {
            "queued_count": counts["queued"],
            "running_count": counts["running"],
            "completed_count": counts["completed"],
            "failed_count": counts["failed"],
            "worker_enabled": self.worker_enabled,
            "max_concurrent_tasks": self.max_concurrent_tasks,
        }

    def wake_worker(self) -> None:
        if self._wake_event is not None:
            self._wake_event.set()

    def cancel_task(self, task_id: str) -> ScheduledTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        if task.status in {"completed", "failed", "cancelled"}:
            return task
        task.status = "cancelled"
        task.updated_at = utc_now_iso()
        task.finished_at = task.updated_at
        task.error = "cancelled"
        return self.store.save_task(task)

    def mark_completed(
        self,
        task_id: str,
        result: dict[str, Any] | None = None,
    ) -> ScheduledTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        task.status = "completed"
        task.result = dict(result or {})
        task.error = None
        task.updated_at = utc_now_iso()
        task.finished_at = task.updated_at
        return self.store.save_task(task)

    def mark_failed(
        self,
        task_id: str,
        error: str,
        *,
        result: dict[str, Any] | None = None,
    ) -> ScheduledTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        task.status = "failed"
        task.result = dict(result or {})
        task.error = error
        task.updated_at = utc_now_iso()
        task.finished_at = task.updated_at
        return self.store.save_task(task)

    def resolve_dependencies(self, task_id: str) -> dict[str, list[str]]:
        task = self.get_task(task_id)
        if task is None:
            return {"completed": [], "pending": [], "failed": [task_id]}
        completed: list[str] = []
        pending: list[str] = []
        failed: list[str] = []
        for dependency_id in task.depends_on:
            dependency = self.get_task(dependency_id)
            if dependency is None or dependency.status in {
                "failed",
                "blocked",
                "cancelled",
                "interrupted",
            }:
                failed.append(dependency_id)
            elif dependency.status == "completed":
                completed.append(dependency_id)
            else:
                pending.append(dependency_id)
        return {
            "completed": completed,
            "pending": pending,
            "failed": failed,
        }

    def enqueue_tool_chain(
        self,
        tool_slugs: list[str],
        *,
        initial_payload: dict[str, Any] | None = None,
        title: str = "Tool chain",
        priority: str = "medium",
        metadata: dict[str, Any] | None = None,
        max_retries: int = 0,
        retry_delay_seconds: float = 0.0,
    ) -> list[ScheduledTask]:
        chain_id = f"chain_{uuid4().hex}"
        tasks: list[ScheduledTask] = []
        previous_id: str | None = None
        for position, slug in enumerate(tool_slugs):
            task = self.enqueue_task(
                title=f"{title} [{position + 1}/{len(tool_slugs)}] {slug}",
                kind="tool_execution",
                priority=priority,
                payload={
                    "tool_slug": slug,
                    **(dict(initial_payload or {}) if position == 0 else {}),
                },
                depends_on=[previous_id] if previous_id else [],
                metadata={
                    **dict(metadata or {}),
                    "chain_id": chain_id,
                    "chain_position": position,
                    "chain_size": len(tool_slugs),
                },
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
            )
            tasks.append(task)
            previous_id = task.task_id
        return tasks

    def enqueue_composite_task(
        self,
        *,
        title: str,
        depends_on: list[str],
        priority: str = "medium",
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledTask:
        return self.enqueue_task(
            title=title,
            kind="composite",
            priority=priority,
            depends_on=depends_on,
            metadata=metadata,
        )

    async def _execute(
        self,
        task: ScheduledTask,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if task.kind == "tool_execution":
            slug = str(payload.pop("tool_slug", "") or "")
            if not slug:
                return {"ok": False, "error": "tool_slug_required"}
            return (
                await self.tool_runtime.execute_tool(slug, payload)
            ).to_dict()
        if task.kind == "agent_execution":
            slug = str(payload.get("agent_slug") or payload.get("agent") or "")
            text = str(payload.get("text") or "")
            if not slug:
                return {"ok": False, "error": "agent_slug_required"}
            result = await self._agents().run_agent(
                slug,
                text,
                context={"scheduler_task_id": task.task_id},
                metadata=task.metadata,
            )
            return result.to_dict()
        if task.kind == "goal_execution":
            objective = str(payload.get("objective") or "")
            if not objective:
                return {"ok": False, "error": "goal_objective_required"}
            result = await self._goals().run_goal(
                objective,
                source=str(payload.get("source") or "scheduler"),
            )
            return {"ok": result.get("status") not in {"failed", "refused"}, "data": result}
        if task.kind == "notification":
            message = str(payload.get("message") or "")
            if self.notifier is not None:
                notified = self.notifier(message)
                if hasattr(notified, "__await__"):
                    await notified
            return {"ok": True, "response": message, "data": {"message": message}}
        if task.kind == "composite":
            dependency_results = self._dependency_results(task)
            merged_data: dict[str, Any] = {}
            for result in dependency_results:
                data = result.get("data")
                if isinstance(data, dict):
                    merged_data.update(data)
            return {
                "ok": True,
                "data": {
                    **merged_data,
                    "dependency_results": dependency_results,
                },
            }
        return {"ok": False, "error": f"unsupported_task_kind: {task.kind}"}

    def _payload_with_dependency_results(
        self,
        task: ScheduledTask,
    ) -> dict[str, Any]:
        payload = dict(task.payload)
        dependency_results = self._dependency_results(task)
        for result in dependency_results:
            data = result.get("data")
            if isinstance(data, dict):
                payload.update(data)
        if dependency_results:
            payload["dependency_results"] = dependency_results
        return payload

    def _dependency_results(self, task: ScheduledTask) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for dependency_id in task.depends_on:
            dependency = self.get_task(dependency_id)
            if dependency and isinstance(dependency.result, dict):
                results.append(dict(dependency.result))
        return results

    def _block_failed_dependents(self) -> None:
        for task in self.list_tasks(status="queued"):
            dependencies = self.resolve_dependencies(task.task_id)
            if dependencies["failed"]:
                self._mark_blocked(
                    task,
                    f"dependency_failed: {', '.join(dependencies['failed'])}",
                )

    def _retry_or_fail(
        self,
        task: ScheduledTask,
        error: str,
        *,
        result: dict[str, Any] | None = None,
    ) -> ScheduledTask | None:
        if self._is_retryable_error(error) and task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = "queued"
            task.result = dict(result or {})
            task.error = error
            task.updated_at = utc_now_iso()
            task.started_at = None
            task.finished_at = None
            retry_at = datetime.now(timezone.utc) + timedelta(
                seconds=task.retry_delay_seconds
            )
            task.metadata = {
                **task.metadata,
                "retry_not_before": retry_at.isoformat(),
                "last_retry_error": error,
            }
            saved = self.store.save_task(task)
            self.wake_worker()
            return saved
        return self.mark_failed(task.task_id, error, result=result)

    def _is_retryable_error(self, error: str) -> bool:
        permanent = {
            "tool_not_found",
            "unsafe_tool_rejected",
            "tool_handler_not_available",
            "tool_slug_required",
            "agent_slug_required",
            "goal_objective_required",
        }
        normalized = error.strip().lower()
        return (
            normalized not in permanent
            and not normalized.startswith("unsupported_task_kind")
        )

    def _retry_is_ready(self, task: ScheduledTask) -> bool:
        value = task.metadata.get("retry_not_before")
        if not value:
            return True
        try:
            retry_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return True
        return datetime.now(timezone.utc) >= retry_at

    def _ready_tasks(self) -> list[ScheduledTask]:
        self._block_failed_dependents()
        ready = [
            task
            for task in self.list_tasks(status="queued")
            if self._retry_is_ready(task)
            and not self.resolve_dependencies(task.task_id)["pending"]
            and not self.resolve_dependencies(task.task_id)["failed"]
        ]
        ready.sort(
            key=lambda task: (
                -PRIORITY_WEIGHT.get(task.priority, 2),
                task.created_at,
            )
        )
        return ready

    async def _worker_loop(self) -> None:
        while self.worker_enabled:
            await self.run_worker_once(wait=False)
            wake_event = self._wake_event
            if wake_event is None:
                await asyncio.sleep(self.worker_poll_interval)
                continue
            wake_event.clear()
            try:
                await asyncio.wait_for(
                    wake_event.wait(),
                    timeout=self.worker_poll_interval,
                )
            except TimeoutError:
                pass

    def _discard_finished_worker_tasks(self) -> None:
        self._active_tasks = {
            task for task in self._active_tasks if not task.done()
        }

    def _mark_blocked(
        self,
        task: ScheduledTask,
        error: str,
    ) -> ScheduledTask:
        task.status = "blocked"
        task.error = error
        task.updated_at = utc_now_iso()
        task.finished_at = task.updated_at
        return self.store.save_task(task)

    def _agents(self):
        if self._agent_runtime is None:
            from core.agent_runtime.runtime import get_agent_runtime

            self._agent_runtime = get_agent_runtime()
        return self._agent_runtime

    def _goals(self):
        if self._goal_orchestrator is None:
            from core.goals.goal_orchestrator import get_goal_orchestrator

            self._goal_orchestrator = get_goal_orchestrator()
        return self._goal_orchestrator


_SCHEDULER: TaskScheduler | None = None
_SCHEDULER_LOCK = threading.Lock()


def get_task_scheduler() -> TaskScheduler:
    global _SCHEDULER
    with _SCHEDULER_LOCK:
        if _SCHEDULER is None:
            _SCHEDULER = TaskScheduler()
        return _SCHEDULER


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
