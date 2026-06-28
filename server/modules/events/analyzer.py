from __future__ import annotations

import logging

from modules.events.event import Event
from modules.events.event_bus import event_bus

logger = logging.getLogger("neron.events.analyzer")


async def analyze_event(event: Event) -> None:
    payload = event.payload or {}

    if event.type == "agent.executed":
        success = payload.get("success")
        duration = payload.get("execution_time_ms")
        agent = payload.get("agent")
        intent = payload.get("intent")

        if success is False:
            await event_bus.publish(Event(
                type="system.alert",
                source="event.analyzer",
                payload={
                    "level": "warning",
                    "reason": "agent_execution_failed",
                    "agent": agent,
                    "intent": intent,
                    "execution_time_ms": duration,
                },
            ))
            return

        if isinstance(duration, (int, float)) and duration > 10000:
            await event_bus.publish(Event(
                type="system.alert",
                source="event.analyzer",
                payload={
                    "level": "warning",
                    "reason": "agent_execution_slow",
                    "agent": agent,
                    "intent": intent,
                    "execution_time_ms": duration,
                },
            ))
            return

    if event.type == "response.ready":
        response_length = payload.get("response_length")
        agent = payload.get("agent")
        intent = payload.get("intent")

        if response_length == 0:
            await event_bus.publish(Event(
                type="system.alert",
                source="event.analyzer",
                payload={
                    "level": "warning",
                    "reason": "empty_response",
                    "agent": agent,
                    "intent": intent,
                },
            ))
