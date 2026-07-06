from __future__ import annotations

import logging

from modules.events.event import Event


logger = logging.getLogger("neron.events.alert_notifier")


async def notify_system_alert(event: Event) -> None:
    payload = event.payload or {}

    level = payload.get("level", "warning")
    reason = payload.get("reason", "unknown")
    agent = payload.get("agent", "n/a")
    intent = payload.get("intent", "n/a")
    execution_time_ms = payload.get("execution_time_ms")

    message = (
        "⚠️ Alerte Néron\n"
        f"Niveau : {level}\n"
        f"Raison : {reason}\n"
        f"Agent : {agent}\n"
        f"Intent : {intent}"
    )

    if execution_time_ms is not None:
        message += f"\nTemps : {execution_time_ms} ms"

    logger.info("system_alert: %s", message)
