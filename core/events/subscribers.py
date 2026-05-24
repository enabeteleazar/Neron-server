from __future__ import annotations

import logging

from core.events.event import Event
from core.events.event_bus import event_bus
from core.events import event_types
from core.events.persistence import persist_event
from core.events.analyzer import analyze_event
from core.self_model.subscriber import update_self_model_from_event
from core.events.alert_notifier import notify_system_alert
from core.self_repair.subscriber import handle_system_alert_for_repair
from core.runtime.governor import handle_self_model_governor_event

logger = logging.getLogger("neron.events.subscribers")


async def log_event(event: Event) -> None:
    payload = event.payload or {}

    if event.type == "system.alert":
        logger.warning(
            "SYSTEM_ALERT level=%s reason=%s agent=%s intent=%s execution_time_ms=%s",
            payload.get("level"),
            payload.get("reason"),
            payload.get("agent"),
            payload.get("intent"),
            payload.get("execution_time_ms"),
        )
        return

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


_SUBSCRIBERS_REGISTERED = False


def register_default_subscribers() -> None:
    global _SUBSCRIBERS_REGISTERED

    if _SUBSCRIBERS_REGISTERED:
        logger.info("default_event_subscribers_already_registered")
        return

    logger.info("default_event_subscribers_registering")

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
        event_bus.subscribe(event_type, persist_event)
        event_bus.subscribe(event_type, analyze_event)
        event_bus.subscribe(event_type, update_self_model_from_event)

        if event_type == event_types.SYSTEM_ALERT:
            event_bus.subscribe(event_type, notify_system_alert)
            event_bus.subscribe(event_type, handle_system_alert_for_repair)

    event_bus.subscribe("self_model.state_changed", log_event)
    event_bus.subscribe("self_model.state_changed", handle_self_model_governor_event)

    event_bus.subscribe("self_model.runtime_mode_changed", log_event)
    event_bus.subscribe("self_model.runtime_mode_changed", handle_self_model_governor_event)

    _SUBSCRIBERS_REGISTERED = True
    logger.info("default_event_subscribers_registered")
