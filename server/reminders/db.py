from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(__file__).parent / "neron_reminders.db"


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_reminder(data: dict[str, Any]) -> dict[str, Any]:
    reminder_id = str(uuid.uuid4())
    created_at = _utc_now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO reminders "
            "(id, content, source, trigger_at, recurrence_rule, status, "
            " channel, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
            (
                reminder_id,
                data["content"],
                data.get("source", "utilisateur"),
                data["trigger_at"],
                data.get("recurrence_rule"),
                data.get("channel"),
                data.get("metadata"),
                created_at,
            ),
        )
    return get_reminder(reminder_id)  # type: ignore[return-value]


def get_reminder(reminder_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
        ).fetchone()
    return dict(row) if row else None


def list_reminders(status_filter: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    with _connect() as conn:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM reminders WHERE status = ? "
                "ORDER BY trigger_at ASC LIMIT ?",
                (status_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM reminders ORDER BY trigger_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def update_reminder(reminder_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    if not fields:
        return get_reminder(reminder_id)
    allowed = {
        "content", "trigger_at", "recurrence_rule", "status", "channel",
        "notified_at", "notification_error", "metadata",
        "triggered_at", "dismissed_at",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_reminder(reminder_id)
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with _connect() as conn:
        conn.execute(
            f"UPDATE reminders SET {set_clause} WHERE id = ?",
            (*updates.values(), reminder_id),
        )
    return get_reminder(reminder_id)


def delete_reminder(reminder_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    return cur.rowcount > 0
