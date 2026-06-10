from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


DEFAULT_DATABASE_PATH = Path("/etc/neron/data/neron_state.sqlite3")

_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.RLock] = {}


def get_path_lock(path: Path | str) -> threading.RLock:
    key = str(Path(path).resolve())
    with _LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(key, threading.RLock())


class SQLiteStore:
    def __init__(self, path: Path | str = DEFAULT_DATABASE_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = get_path_lock(self.path)
        self.migrate()

    def migrate(self) -> None:
        statements = (
            """
                CREATE TABLE IF NOT EXISTS goals (
                    goal_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    current_step TEXT,
                    progress REAL NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    payload TEXT NOT NULL
                )
            """,
            """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    goal_id TEXT,
                    plan_id TEXT,
                    status TEXT NOT NULL,
                    current_step TEXT,
                    progress INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    payload TEXT NOT NULL
                )
            """,
            """
                CREATE INDEX IF NOT EXISTS idx_projects_goal_id
                    ON projects(goal_id)
            """,
            """
                CREATE INDEX IF NOT EXISTS idx_projects_plan_id
                    ON projects(plan_id)
            """,
            """
                CREATE TABLE IF NOT EXISTS workflows (
                    plan_id TEXT PRIMARY KEY,
                    goal_id TEXT,
                    status TEXT NOT NULL,
                    current_step TEXT,
                    updated_at REAL NOT NULL,
                    payload TEXT NOT NULL
                )
            """,
            """
                CREATE INDEX IF NOT EXISTS idx_workflows_goal_id
                    ON workflows(goal_id)
            """,
            """
                CREATE TABLE IF NOT EXISTS workflow_steps (
                    owner_type TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    name TEXT,
                    status TEXT,
                    occurred_at TEXT,
                    error TEXT,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (owner_type, owner_id, position)
                )
            """,
            """
                CREATE TABLE IF NOT EXISTS test_results (
                    project_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    name TEXT,
                    returncode INTEGER,
                    ran_at TEXT,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (project_id, position)
                )
            """,
        )
        with self._transaction() as connection:
            for statement in statements:
                connection.execute(statement)

    def upsert_goal(self, goal: dict[str, Any]) -> None:
        goal_id = str(goal["id"])
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO goals (
                    goal_id, status, current_step, progress,
                    created_at, updated_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(goal_id) DO UPDATE SET
                    status = excluded.status,
                    current_step = excluded.current_step,
                    progress = excluded.progress,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    goal_id,
                    str(goal.get("status") or "pending"),
                    str(goal.get("current_step") or goal.get("status") or "pending"),
                    float(goal.get("progress") or 0),
                    float(goal.get("created_at") or 0),
                    float(goal.get("updated_at") or goal.get("created_at") or 0),
                    self._dump(goal),
                ),
            )

    def get_goal(self, goal_id: str) -> dict[str, Any] | None:
        return self._fetch_payload(
            "SELECT payload FROM goals WHERE goal_id = ?",
            (goal_id,),
        )

    def list_goals(self) -> list[dict[str, Any]]:
        return self._fetch_payloads(
            "SELECT payload FROM goals ORDER BY created_at ASC"
        )

    def upsert_project(self, project: dict[str, Any]) -> None:
        project_id = str(project["project_id"])
        metadata = project.get("metadata") or {}
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO projects (
                    project_id, goal_id, plan_id, status, current_step,
                    progress, created_at, updated_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    goal_id = excluded.goal_id,
                    plan_id = excluded.plan_id,
                    status = excluded.status,
                    current_step = excluded.current_step,
                    progress = excluded.progress,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    project_id,
                    self._optional_text(metadata.get("goal_id")),
                    self._optional_text(metadata.get("plan_id")),
                    str(project.get("status") or "pending"),
                    self._optional_text(project.get("current_step")),
                    int(project.get("progress") or 0),
                    float(project.get("created_at") or 0),
                    float(project.get("updated_at") or project.get("created_at") or 0),
                    self._dump(project),
                ),
            )
            self._replace_steps(
                connection,
                owner_type="project",
                owner_id=project_id,
                steps=list(project.get("steps") or []),
            )
            connection.execute(
                "DELETE FROM test_results WHERE project_id = ?",
                (project_id,),
            )
            for position, result in enumerate(project.get("test_results") or []):
                connection.execute(
                    """
                    INSERT INTO test_results (
                        project_id, position, name, returncode, ran_at, payload
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        position,
                        self._optional_text(result.get("name")),
                        result.get("returncode"),
                        self._optional_text(result.get("ran_at")),
                        self._dump(result),
                    ),
                )

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self._fetch_payload(
            "SELECT payload FROM projects WHERE project_id = ?",
            (project_id,),
        )

    def list_projects(self) -> list[dict[str, Any]]:
        return self._fetch_payloads(
            "SELECT payload FROM projects ORDER BY created_at ASC"
        )

    def find_project_by_tracking(
        self,
        *,
        goal_id: str | None = None,
        plan_id: str | None = None,
    ) -> dict[str, Any] | None:
        if goal_id:
            result = self._fetch_payload(
                """
                SELECT payload FROM projects
                WHERE goal_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (goal_id,),
            )
            if result is not None:
                return result
        if plan_id:
            return self._fetch_payload(
                """
                SELECT payload FROM projects
                WHERE plan_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (plan_id,),
            )
        return None

    def upsert_workflow(self, workflow: dict[str, Any]) -> None:
        plan_id = str(workflow["id"])
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO workflows (
                    plan_id, goal_id, status, current_step, updated_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(plan_id) DO UPDATE SET
                    goal_id = excluded.goal_id,
                    status = excluded.status,
                    current_step = excluded.current_step,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    plan_id,
                    self._optional_text(workflow.get("goal_id")),
                    str(workflow.get("status") or "pending"),
                    self._optional_text(workflow.get("current_step")),
                    self._workflow_timestamp(workflow),
                    self._dump(workflow),
                ),
            )
            self._replace_steps(
                connection,
                owner_type="workflow",
                owner_id=plan_id,
                steps=list(workflow.get("steps") or []),
            )

    def get_workflow(self, plan_id: str) -> dict[str, Any] | None:
        return self._fetch_payload(
            "SELECT payload FROM workflows WHERE plan_id = ?",
            (plan_id,),
        )

    def find_workflow_by_goal(self, goal_id: str) -> dict[str, Any] | None:
        return self._fetch_payload(
            """
            SELECT payload FROM workflows
            WHERE goal_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (goal_id,),
        )

    def list_workflows(self) -> list[dict[str, Any]]:
        return self._fetch_payloads(
            "SELECT payload FROM workflows ORDER BY updated_at ASC"
        )

    def workflow_steps(
        self,
        *,
        owner_type: str,
        owner_id: str,
    ) -> list[dict[str, Any]]:
        return self._fetch_payloads(
            """
            SELECT payload FROM workflow_steps
            WHERE owner_type = ? AND owner_id = ?
            ORDER BY position ASC
            """,
            (owner_type, owner_id),
        )

    def journal_mode(self) -> str:
        with self._connect() as connection:
            row = connection.execute("PRAGMA journal_mode").fetchone()
        return str(row[0]).lower() if row else ""

    def busy_timeout(self) -> int:
        with self._connect() as connection:
            row = connection.execute("PRAGMA busy_timeout").fetchone()
        return int(row[0]) if row else 0

    def _replace_steps(
        self,
        connection: sqlite3.Connection,
        *,
        owner_type: str,
        owner_id: str,
        steps: list[dict[str, Any]],
    ) -> None:
        connection.execute(
            "DELETE FROM workflow_steps WHERE owner_type = ? AND owner_id = ?",
            (owner_type, owner_id),
        )
        for position, step in enumerate(steps):
            connection.execute(
                """
                INSERT INTO workflow_steps (
                    owner_type, owner_id, position, name, status,
                    occurred_at, error, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    owner_type,
                    owner_id,
                    position,
                    self._optional_text(step.get("name") or step.get("title")),
                    self._optional_text(step.get("status")),
                    self._optional_text(step.get("at") or step.get("completed_at")),
                    self._optional_text(step.get("error")),
                    self._dump(step),
                ),
            )

    def _fetch_payload(
        self,
        query: str,
        parameters: tuple[Any, ...] = (),
    ) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(query, parameters).fetchone()
        return self._load_payload(row["payload"]) if row else None

    def _fetch_payloads(
        self,
        query: str,
        parameters: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._load_payload(row["payload"]) for row in rows]

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self.path,
            timeout=5.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        try:
            yield connection
        finally:
            connection.close()

    def _workflow_timestamp(self, workflow: dict[str, Any]) -> float:
        for key in ("updated_at", "finished_at", "execution_started_at", "created_at"):
            value = workflow.get(key)
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    continue
        return time.time()

    def _dump(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _load_payload(self, payload: str) -> dict[str, Any]:
        value = json.loads(payload)
        return value if isinstance(value, dict) else {}

    def _optional_text(self, value: Any) -> str | None:
        if value is None or value == "":
            return None
        return str(value)
