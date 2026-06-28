from __future__ import annotations

import logging

from modules.events.event import Event
from modules.events.event_bus import event_bus
from modules.events import event_types
from modules.events.persistence import persist_event
from modules.events.analyzer import analyze_event
from modules.self_model.subscriber import update_self_model_from_event
from modules.events.alert_notifier import notify_system_alert
from modules.self_repair.subscriber import handle_system_alert_for_repair
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


def register_default_subscribers() -> None:
    logger.info("default_event_subscribers_registering")

    event_bus.subscribe("*", log_event)
    event_bus.subscribe("*", persist_event)

    for event_type in (
        event_types.USER_MESSAGE_RECEIVED,
        event_types.INTENT_DETECTED,
        event_types.AGENT_SELECTED,
        event_types.AGENT_EXECUTED,
        event_types.AGENT_CONSULTED,
        event_types.RESPONSE_READY,
        event_types.SYSTEM_ALERT,
    ):
        event_bus.subscribe(event_type, analyze_event)
        event_bus.subscribe(event_type, update_self_model_from_event)

        if event_type == event_types.SYSTEM_ALERT:
            event_bus.subscribe(event_type, notify_system_alert)
            event_bus.subscribe(event_type, handle_system_alert_for_repair)

    for event_type in (
        event_types.MEMORY_UPDATED,
        event_types.WORLD_MODEL_STATE_CHANGED,
        event_types.WORLD_MODEL_OBSERVATION_UPDATED,
    ):
        event_bus.subscribe(event_type, update_self_model_from_event)

    for event_type in (
        event_types.SELF_MODEL_STATE_CHANGED,
        event_types.SELF_MODEL_RUNTIME_MODE_CHANGED,
    ):
        event_bus.subscribe(event_type, handle_self_model_governor_event)

    logger.info("default_event_subscribers_registered")
