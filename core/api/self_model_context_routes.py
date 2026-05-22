from __future__ import annotations

from fastapi import APIRouter

from core.self_model.self_model import get_self_model
from core.task_system.task_manager import get_task_manager

router = APIRouter(tags=["self-model-context"])


@router.get("/self-model/context")
async def self_model_context() -> dict:
    model = get_self_model()
    task_manager = get_task_manager()

    model.refresh()

    data = model.to_dict()
    runtime = data.get("runtime", {}) or {}

    try:
        tasks_all = task_manager.list_tasks()
    except Exception:
        tasks_all = []

    try:
        active_tasks = task_manager.list_active_tasks()
    except Exception:
        try:
            active_tasks = task_manager.get_active_tasks()
        except Exception:
            active_tasks = []

    pending_tasks = [
        task for task in tasks_all
        if task.get("status") in {"pending", "todo", "queued"}
    ]

    failed_tasks = [
        task for task in tasks_all
        if task.get("status") in {"failed", "error"}
    ]

    running_tasks = [
        task for task in tasks_all
        if task.get("status") in {"running", "in_progress"}
    ]

    next_task = pending_tasks[0] if pending_tasks else None

    task_summary = {
        "total": len(tasks_all),
        "active": len(active_tasks),
        "pending": len(pending_tasks),
        "running": len(running_tasks),
        "failed": len(failed_tasks),
    }

    return {
        "identity": data.get("identity"),
        "health": {
            "realtime": data.get("health_realtime"),
            "historical": data.get("health_historical"),
            "global": data.get("health_global"),
        },
        "goal": data.get("active_goal"),
        "tasks": {
            "summary": task_summary,
            "next": next_task,
            "running": running_tasks,
        },
        "diagnostics": data.get("diagnostics", []),
        "recommendations": data.get("recommendations", []),
        "summary": data.get("cognitive_summary"),
        "runtime": runtime,
        "last_activity": {
            "last_event": data.get("last_event"),
            "last_intent": data.get("last_intent"),
            "last_agent": data.get("last_agent"),
        },
    }
