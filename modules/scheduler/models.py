from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


TASK_KINDS = {
    "tool_execution",
    "agent_execution",
    "goal_execution",
    "notification",
    "composite",
}

TASK_STATUSES = {
    "queued",
    "running",
    "completed",
    "failed",
    "blocked",
    "cancelled",
    "interrupted",
}

TASK_PRIORITIES = {"low", "medium", "high", "critical"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ScheduledTask:
    title: str
    kind: str
    task_id: str = field(default_factory=lambda: f"task_{uuid4().hex}")
    status: str = "queued"
    priority: str = "medium"
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    depends_on: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    started_at: str | None = None
    finished_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    max_retries: int = 0
    retry_count: int = 0
    retry_delay_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in TASK_KINDS:
            raise ValueError(f"Invalid scheduled task kind: {self.kind}")
        if self.status not in TASK_STATUSES:
            raise ValueError(f"Invalid scheduled task status: {self.status}")
        if self.priority not in TASK_PRIORITIES:
            raise ValueError(f"Invalid scheduled task priority: {self.priority}")
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Scheduled task title is required")
        self.depends_on = list(dict.fromkeys(map(str, self.depends_on)))
        self.max_retries = max(0, int(self.max_retries))
        self.retry_count = max(0, int(self.retry_count))
        self.retry_delay_seconds = max(0.0, float(self.retry_delay_seconds))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ScheduledTask":
        return cls(
            task_id=str(payload["task_id"]),
            title=str(payload["title"]),
            kind=str(payload["kind"]),
            status=str(payload.get("status") or "queued"),
            priority=str(payload.get("priority") or "medium"),
            payload=dict(payload.get("payload") or {}),
            result=(
                dict(payload["result"])
                if isinstance(payload.get("result"), dict)
                else None
            ),
            error=str(payload["error"]) if payload.get("error") else None,
            depends_on=list(payload.get("depends_on") or []),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            updated_at=str(payload.get("updated_at") or utc_now_iso()),
            started_at=payload.get("started_at"),
            finished_at=payload.get("finished_at"),
            metadata=dict(payload.get("metadata") or {}),
            max_retries=int(payload.get("max_retries") or 0),
            retry_count=int(payload.get("retry_count") or 0),
            retry_delay_seconds=float(payload.get("retry_delay_seconds") or 0),
        )
