from __future__ import annotations

from datetime import datetime


def system_health_check(payload: dict):
    return {
        "success": True,
        "type": "system_health",
        "checked_at": datetime.utcnow().isoformat(),
        "status": "healthy",
    }
