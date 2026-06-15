from __future__ import annotations

import logging

from modules.events.event import Event
from modules.memory.persistent_store import get_store

logger = logging.getLogger("neron.events.persistence")


async def persist_event(event: Event) -> None:
    try:
        store = get_store()
        store.push_event(
            event_id=event.event_id,
            event_type=event.type,
            source=event.source,
            payload=event.payload,
            created_at=event.created_at.isoformat(),
        )
    except Exception as exc:
        logger.warning(
            "event_persist_failed type=%s event_id=%s error=%s",
            event.type,
            event.event_id,
            exc,
        )
