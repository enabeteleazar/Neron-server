from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"service": "watchdog", "status": "healthy"}


@router.get("/status")
async def status(request: Request) -> dict[str, str | float]:
    runtime = request.app.state.watchdog_runtime
    return {
        "service": "watchdog",
        "status": "running",
        "uptime": round(runtime.uptime, 3),
    }
