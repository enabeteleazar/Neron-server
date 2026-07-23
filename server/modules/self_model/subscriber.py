from __future__ import annotations

import logging
from typing import Any

from core.modules.self_model import get_self_model

logger = logging.getLogger("neron.self_model")


async def update_self_model_from_event(event: Any) -> None:
    try:
        logger.info(
            "self_model_event_received type=%s source=%s",
            getattr(event, "type", None),
            getattr(event, "source", None),
        )

        model = get_self_model()
        model.update_from_event(event)

    except Exception as exc:
        event_type = (
            getattr(event, "type", None)
            or getattr(event, "event_type", None)
            or "unknown"
        )

        logger.warning(
            "self_model_update_failed type=%s error=%s",
            event_type,
            exc,
        )


async def handle_event(event: Any) -> None:
    await update_self_model_from_event(event)


async def self_model_event_handler(event: Any) -> None:
    await update_self_model_from_event(event)


async def on_event(event: Any) -> None:
    await update_self_model_from_event(event)
