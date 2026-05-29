"""Small in-process Health Center history."""

from __future__ import annotations

from collections import deque
from typing import Any


class HealthHistory:
    def __init__(self, max_snapshots: int = 50):
        self._snapshots: deque[dict[str, Any]] = deque(maxlen=max_snapshots)
        self._last_status: str | None = None

    def add_snapshot(self, snapshot: dict[str, Any]) -> tuple[str | None, str]:
        previous = self._last_status
        current = snapshot.get("status", "unknown")
        self._snapshots.append(snapshot)
        self._last_status = current
        return previous, current

    def snapshots(self) -> list[dict[str, Any]]:
        return list(self._snapshots)

    @property
    def last_status(self) -> str | None:
        return self._last_status
