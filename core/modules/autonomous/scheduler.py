from __future__ import annotations

try:
    from core.modules.scheduler import get_jobs
except Exception:
    get_jobs = None


class AutonomousScheduler:
    """
    Façade de compatibilité pour les anciens imports :
    agents.autonomous.planner_agent -> core.modules.autonomous.scheduler
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def status(self) -> dict:
        jobs = []
        if get_jobs is not None:
            try:
                jobs = get_jobs()
            except Exception:
                jobs = []

        return {
            "status": "available",
            "compatibility_mode": True,
            "jobs": jobs,
        }

    def get_jobs(self):
        if get_jobs is None:
            return []
        try:
            return get_jobs()
        except Exception:
            return []
