from __future__ import annotations

import logging

from core.events.event import Event
from core.agents.automation.watchdog_agent import send_watchdog_notification

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

    try:
        await send_watchdog_notification(message)
    except TypeError:
        send_watchdog_notification(message)
    except Exception as exc:
        logger.warning("telegram_alert_failed reason=%s error=%s", reason, exc)
