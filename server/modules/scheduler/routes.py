from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from core.api.auth import verify_api_key
from modules.scheduler.scheduler import get_task_scheduler
from modules.scheduler.models import TASK_KINDS, TASK_PRIORITIES, TASK_STATUSES


router = APIRouter(prefix="/tasks", tags=["task-scheduler"])


@router.get("")
async def list_tasks(
    status: str | None = None,
    kind: str | None = None,
    _: None = Depends(verify_api_key),
):
    tasks = get_task_scheduler().list_tasks(status=status, kind=kind)
    return {"count": len(tasks), "tasks": [task.to_dict() for task in tasks]}


@router.get("/status")
async def task_status(_: None = Depends(verify_api_key)):
    return get_task_scheduler().status()


@router.get("/running")
async def running_tasks(_: None = Depends(verify_api_key)):
    tasks = get_task_scheduler().list_tasks(status="running")
    return {"tasks": [task.to_dict() for task in tasks]}


@router.get("/next")
async def next_task(_: None = Depends(verify_api_key)):
    scheduler = get_task_scheduler()
    ready = scheduler._ready_tasks()
    return {"task": ready[0].to_dict() if ready else None}


@router.post("/next/start")
async def run_next_task(_: None = Depends(verify_api_key)):
    task = await get_task_scheduler().run_next()
    if task is None:
        raise HTTPException(status_code=404, detail="No queued task available")
    return {"task": task.to_dict()}


@router.get("/schema")
async def task_schema(_: None = Depends(verify_api_key)):
    return {
        "kinds": sorted(TASK_KINDS),
        "statuses": sorted(TASK_STATUSES),
        "priorities": sorted(TASK_PRIORITIES),
    }


@router.get("/{task_id}")
async def get_task(task_id: str, _: None = Depends(verify_api_key)):
    task = get_task_scheduler().get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    return task.to_dict()


@router.post("/{task_id}/run")
async def run_task(task_id: str, _: None = Depends(verify_api_key)):
    task = await get_task_scheduler().run_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    return task.to_dict()


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, _: None = Depends(verify_api_key)):
    task = get_task_scheduler().cancel_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    return task.to_dict()
