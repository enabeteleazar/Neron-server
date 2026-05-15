from __future__ import annotations

import logging

from core.events.event import Event
from core.self_model.self_model import get_self_model

logger = logging.getLogger("neron.self_model")


async def update_self_model_from_event(event: Event) -> None:
    try:
        model = get_self_model()
        model.update_from_event(
            event_type=event.type,
            payload=event.payload or {},
            created_at=event.created_at.isoformat(),
        )
    except Exception as exc:
        logger.warning("self_model_update_failed type=%s error=%s", event.type, exc)
