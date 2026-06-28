from __future__ import annotations

try:
    from .scheduler import AutonomousScheduler
except Exception:
    AutonomousScheduler = None

__all__ = ["AutonomousScheduler"]
