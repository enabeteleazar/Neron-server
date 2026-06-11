from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.agent_runtime.models import AgentExecutionResult
from core.storage.sqlite_store import DEFAULT_DATABASE_PATH, SQLiteStore


class AgentRuntimeStore:
    def __init__(self, path: Path | str = DEFAULT_DATABASE_PATH) -> None:
        self.sqlite = SQLiteStore(path)

    def save_execution(
        self,
        execution: AgentExecutionResult,
        *,
        request: str,
    ) -> AgentExecutionResult:
        with self.sqlite._transaction() as connection:
            connection.execute(
                """
                INSERT INTO agent_runtime_executions (
                    execution_id, agent_slug, request, status, started_at,
                    finished_at, duration_ms, result, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(execution_id) DO UPDATE SET
                    agent_slug = excluded.agent_slug,
                    status = excluded.status,
                    finished_at = excluded.finished_at,
                    duration_ms = excluded.duration_ms,
                    result = excluded.result,
                    error = excluded.error
                """,
                (
                    execution.execution_id,
                    execution.agent_slug,
                    request,
                    execution.status,
                    execution.started_at,
                    execution.finished_at,
                    execution.duration_ms,
                    json.dumps(
                        {
                            "response": execution.response,
                            "result": execution.result,
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    execution.error,
                ),
            )
        return execution

    def get_execution(self, execution_id: str) -> dict[str, Any] | None:
        with self.sqlite._lock, self.sqlite._connect() as connection:
            row = connection.execute(
                "SELECT * FROM agent_runtime_executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_executions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        with self.sqlite._lock, self.sqlite._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM agent_runtime_executions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def count_executions(self) -> int:
        with self.sqlite._lock, self.sqlite._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM agent_runtime_executions"
            ).fetchone()
        return int(row["count"]) if row else 0

    def last_execution(self) -> dict[str, Any] | None:
        executions = self.list_executions(limit=1)
        return executions[0] if executions else None

    def _from_row(self, row: Any) -> dict[str, Any]:
        stored = json.loads(row["result"] or "{}")
        result = stored.get("result")
        return {
            "execution_id": str(row["execution_id"]),
            "agent_slug": str(row["agent_slug"]),
            "request": str(row["request"]),
            "status": str(row["status"]),
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "duration_ms": row["duration_ms"],
            "response": str(stored.get("response") or ""),
            "result": result if isinstance(result, dict) else {},
            "error": row["error"],
        }
