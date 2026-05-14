from __future__ import annotations

import logging

from core.events.event import Event
from core.events.event_bus import event_bus
from core.events import event_types

logger = logging.getLogger("neron.events.subscribers")


async def log_event(event: Event) -> None:
    payload = event.payload or {}

    details = {
        key: payload.get(key)
        for key in (
            "intent",
            "agent",
            "success",
            "execution_time_ms",
            "response_length",
        )
        if key in payload
    }

    if details:
        logger.info(
            "event_trace type=%s source=%s event_id=%s details=%s",
            event.type,
            event.source,
            event.event_id,
            details,
        )
        return

    logger.info(
        "event_trace type=%s source=%s event_id=%s payload_keys=%s",
        event.type,
        event.source,
        event.event_id,
        list(payload.keys()),
    )


def register_default_subscribers() -> None:
    for event_type in (
        event_types.USER_MESSAGE_RECEIVED,
        event_types.INTENT_DETECTED,
        event_types.AGENT_SELECTED,
        event_types.AGENT_EXECUTED,
        event_types.RESPONSE_READY,
        event_types.SYSTEM_ALERT,
        event_types.MEMORY_UPDATED,
    ):
        event_bus.subscribe(event_type, log_event)
