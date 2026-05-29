"""WorldModel compatibility adapter backed by Health Center."""

from __future__ import annotations

from typing import Any

from .health.snapshot import health_center


async def get_environment_state() -> dict[str, Any]:
    """Interpret Néron's runtime environment from Health Center.

    WorldModel keeps its role of describing the environment, but consumes the
    shared normalized health snapshot instead of collecting system metrics again.
    """

    snapshot = await health_center.create_snapshot()
    return {
        "environment": "runtime",
        "status": snapshot["status"],
        "health_center": {
            "resources": snapshot.get("resources", {}),
            "events": snapshot.get("events", []),
            "recommendations": snapshot.get("recommendations", []),
        },
        "timestamp": snapshot["timestamp"],
    }
