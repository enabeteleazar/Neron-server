"""SelfModel compatibility adapter backed by Health Center."""

from __future__ import annotations

from typing import Any

from .health.snapshot import health_center


async def get_self_state() -> dict[str, Any]:
    """Interpret Néron's internal state from Health Center.

    This avoids duplicating CPU/RAM/service collection in SelfModel while keeping
    a small, stable payload for existing consumers.
    """

    snapshot = await health_center.create_snapshot()
    return {
        "identity": "neron",
        "status": snapshot["status"],
        "internal_health": {
            "services": snapshot.get("services", {}),
            "resources": snapshot.get("resources", {}),
            "diagnostics": snapshot.get("diagnostics", []),
        },
        "timestamp": snapshot["timestamp"],
    }
