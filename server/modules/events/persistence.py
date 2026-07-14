from __future__ import annotations

import logging

from modules.events.event import Event
from modules.memory.persistent_store import store_memory

logger = logging.getLogger("neron.events.persistence")


async def persist_event(event: Event) -> None:
    try:
        await store_memory(
            content=f"[EVENT] {event.type}",
            metadata={
                "event_id": event.event_id,
                "source": event.source,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            },
        )

    except Exception as exc:
        logger.warning(
            "event_persist_failed type=%s event_id=%s error=%s",
            event.type,
            event.event_id,
            exc,
        )
