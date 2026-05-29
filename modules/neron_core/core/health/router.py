"""FastAPI router for the Health Center API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from .snapshot import health_center

router = APIRouter(prefix="/health-center", tags=["health-center"])


@router.get("/status")
async def get_health_center_status() -> dict[str, Any]:
    """Return a normalized health snapshot.

    The public shape intentionally matches the migration contract and does not
    replace the legacy ``/health`` endpoint.
    """

    return await health_center.create_snapshot()


def configure_health_center(agents: dict[str, Any] | None = None) -> None:
    health_center.configure(agents)
