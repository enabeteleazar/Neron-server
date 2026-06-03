from fastapi import APIRouter, Query

from core.runtime.events.event_store import read_events


router = APIRouter(prefix="/events", tags=["events"])


@router.get("/recent")
def recent_events(
    limit: int = Query(default=20, ge=1, le=100),
    event_type: str | None = None,
):
    return {
        "count": limit,
        "event_type": event_type,
        "events": read_events(limit=limit, event_type=event_type),
    }
