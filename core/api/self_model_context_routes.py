from __future__ import annotations

from fastapi import APIRouter

from core.self_model.self_model import get_self_model
from core.task_system.task_manager import get_task_manager

router = APIRouter(tags=["self-model-context"])


@router.get("/self-model/context")
async def self_model_context() -> dict:
    model = get_self_model()
    task_manager = get_task_manager()

    model.collect_runtime()

    data = model.to_dict()
    task_summary = task_manager.get_status_summary()
    next_task = task_manager.get_next_task()
    running_tasks = task_manager.list_running_tasks()

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
        "runtime": {
            "cpu_usage": data.get("runtime", {}).get("cpu_usage"),
            "ram_usage": data.get("runtime", {}).get("ram_usage"),
            "disk_usage": data.get("runtime", {}).get("disk_usage"),
            "uptime_seconds": data.get("runtime", {}).get("uptime_seconds"),
        },
        "last_activity": {
            "last_event": data.get("last_event"),
            "last_intent": data.get("last_intent"),
            "last_agent": data.get("last_agent"),
        },
    }
