"""Doctor integration (health / diagnostics).

Doctor is kept as a compatibility facade during the migration to Health Center.
New code should consume ``modules.neron_core.core.health`` directly, while legacy
imports can continue calling ``run_diagnostics()``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys


def _ensure_core_path() -> None:
    core_path = Path(__file__).resolve().parents[2] / "neron_core"
    if str(core_path) not in sys.path:
        sys.path.insert(0, str(core_path))


def run_diagnostics():
    """Return legacy Doctor diagnostics with a Health Center fallback."""

    try:
        from server.core.scripts.doctor import run as _run

        return _run()
    except Exception:
        pass

    try:
        _ensure_core_path()
        from core.health.snapshot import health_center

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(health_center.create_snapshot())
        return {"status": "unavailable", "reason": "health_center_async_loop_running"}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}
