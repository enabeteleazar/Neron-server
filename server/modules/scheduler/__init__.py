from modules.scheduler.models import ScheduledTask
from modules.scheduler.scheduler import TaskScheduler, get_task_scheduler
from modules.scheduler.store import SchedulerStore


def get_jobs() -> list[dict]:
    """Compatibility wrapper for the legacy scheduler surface."""
    scheduler = get_task_scheduler()
    jobs: list[dict] = []
    for task in scheduler.list_tasks():
        jobs.append(
            {
                "id": task.task_id,
                "name": task.title,
                "next_run": task.metadata.get("next_run")
                or task.metadata.get("scheduled_at")
                or task.created_at,
            }
        )
    return jobs


__all__ = [
    "get_jobs",
    "ScheduledTask",
    "SchedulerStore",
    "TaskScheduler",
    "get_task_scheduler",
]
