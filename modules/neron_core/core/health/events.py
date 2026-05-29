"""Health Center event bridge.

The bridge deliberately stays small: it appends normalized health events to the
existing JSONL event stream when available and mirrors them to the legacy
watchdog SQLite event table on a best-effort basis. This keeps Doctor/Watchdog
compatibility while Health Center becomes the health event producer.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

HEALTH_EVENT_TYPES = {
    "health.snapshot.created",
    "health.status.changed",
    "health.service.unreachable",
    "health.service.recovered",
    "health.resource.warning",
    "health.resource.critical",
    "health.diagnostic.created",
}

HEALTH_LISTENED_EVENT_TYPES = {
    "system.service.started",
    "system.service.stopped",
    "system.service.error",
    "agent.execution.failed",
    "llm.provider.error",
    "watchdog.restart.performed",
    "goal.changed",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_events_path() -> Path:
    configured = os.getenv("NERON_EVENTS_JSONL") or os.getenv("HEALTH_EVENTS_PATH")
    if configured:
        return Path(configured)
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "data" / "events.jsonl"


class HealthEventBus:
    """Append-only JSONL bus used by Health Center.

    It is intentionally file-based because the project already documents
    ``events.jsonl`` and the watchdog owns active restarts rather than a shared
    broker. Tests may pass a temporary path.
    """

    def __init__(self, path: Path | str | None = None, max_recent: int = 100):
        self.path = Path(path) if path else default_events_path()
        self.max_recent = max_recent
        self._lock = Lock()
        self._in_memory_recent: list[dict[str, Any]] = []

    def publish(self, event_type: str, payload: dict[str, Any] | None = None, source: str = "health_center") -> dict[str, Any]:
        event = {
            "type": event_type,
            "source": source,
            "timestamp": utc_now_iso(),
            "payload": payload or {},
        }
        self._append_jsonl(event)
        self._mirror_to_watchdog(event)
        return event

    def ingest(self, event: dict[str, Any], source: str = "external") -> dict[str, Any]:
        event_type = str(event.get("type") or event.get("event") or "system.event")
        normalized = {
            "type": event_type,
            "source": event.get("source", source),
            "timestamp": event.get("timestamp") or utc_now_iso(),
            "payload": event.get("payload") or event.get("data") or event,
        }
        self._append_jsonl(normalized)
        return normalized

    def recent(self, limit: int = 20, relevant_only: bool = False) -> list[dict[str, Any]]:
        events = self._read_jsonl(limit=max(limit * 3, limit))
        if not events:
            events = list(self._in_memory_recent)
        if relevant_only:
            interesting = HEALTH_EVENT_TYPES | HEALTH_LISTENED_EVENT_TYPES
            events = [event for event in events if event.get("type") in interesting]
        return events[-limit:]

    def _append_jsonl(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._in_memory_recent.append(event)
            self._in_memory_recent = self._in_memory_recent[-self.max_recent:]
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(event, ensure_ascii=False) + "\n")
            except OSError:
                # Health must keep working even when the event volume is read-only.
                pass

    def _read_jsonl(self, limit: int) -> list[dict[str, Any]]:
        try:
            if not self.path.exists():
                return []
            lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        except OSError:
            return []
        events: list[dict[str, Any]] = []
        for line in lines:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def _mirror_to_watchdog(self, event: dict[str, Any]) -> None:
        try:
            from agents.watchdog_agent import log_event

            log_event(
                event.get("type", "health.event"),
                service="health_center",
                message=event.get("type"),
                data=event.get("payload", {}),
            )
        except Exception:
            pass


def filter_relevant_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    interesting = HEALTH_EVENT_TYPES | HEALTH_LISTENED_EVENT_TYPES
    return [event for event in events if event.get("type") in interesting]
