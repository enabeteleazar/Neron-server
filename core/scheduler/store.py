from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.scheduler.models import ScheduledTask
from core.storage.sqlite_store import DEFAULT_DATABASE_PATH, SQLiteStore


class SchedulerStore:
    def __init__(self, path: Path | str = DEFAULT_DATABASE_PATH) -> None:
        self.sqlite = SQLiteStore(path)

    def save_task(self, task: ScheduledTask) -> ScheduledTask:
        payload = task.to_dict()
        with self.sqlite._transaction() as connection:
            connection.execute(
                """
                INSERT INTO scheduler_tasks (
                    task_id, kind, status, priority,
                    created_at, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    kind = excluded.kind,
                    status = excluded.status,
                    priority = excluded.priority,
                    updated_at = excluded.updated_at,
                    payload_json = excluded.payload_json
                """,
                (
                    task.task_id,
                    task.kind,
                    task.status,
                    task.priority,
                    task.created_at,
                    task.updated_at,
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            )
        return task

    def get_task(self, task_id: str) -> ScheduledTask | None:
        with self.sqlite._lock, self.sqlite._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM scheduler_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return self._from_payload(row["payload_json"]) if row else None

    def list_tasks(
        self,
        *,
        status: str | None = None,
        kind: str | None = None,
    ) -> list[ScheduledTask]:
        conditions: list[str] = []
        parameters: list[Any] = []
        if status:
            conditions.append("status = ?")
            parameters.append(status)
        if kind:
            conditions.append("kind = ?")
            parameters.append(kind)
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = (
            "SELECT payload_json FROM scheduler_tasks"
            f"{where} ORDER BY created_at ASC"
        )
        with self.sqlite._lock, self.sqlite._connect() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._from_payload(row["payload_json"]) for row in rows]

    def recover_running_tasks(
        self,
        reason: str = "scheduler_restarted",
    ) -> list[ScheduledTask]:
        recovered: list[ScheduledTask] = []
        for task in self.list_tasks(status="running"):
            now = datetime.now(timezone.utc).isoformat()
            task.status = "interrupted"
            task.error = "Execution interrupted by scheduler restart"
            task.updated_at = now
            task.finished_at = now
            task.metadata = {
                **task.metadata,
                "recovery_reason": reason,
                "recovered_at": now,
            }
            recovered.append(self.save_task(task))
        return recovered

    def _from_payload(self, payload: str) -> ScheduledTask:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Invalid scheduler task payload")
        return ScheduledTask.from_dict(data)
