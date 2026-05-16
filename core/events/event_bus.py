from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from core.events.event import Event

logger = logging.getLogger("neron.events")

Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers[event_type].append(handler)
        logger.debug("event_subscribed type=%s handler=%s", event_type, getattr(handler, "__name__", str(handler)))

    async def publish(self, event: Event) -> None:
        handlers = list(self._subscribers.get(event.type, []))
        handler_names = [
            getattr(handler, "__name__", str(handler))
            for handler in handlers
        ]

        logger.info(
            "event_published type=%s source=%s event_id=%s handlers=%s handler_names=%s",
            event.type,
            event.source,
            event.event_id,
            len(handlers),
            handler_names,
        )

        if not handlers:
            return

        results = await asyncio.gather(
            *(handler(event) for handler in handlers),
            return_exceptions=True,
        )

        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(
                    "event_handler_failed type=%s handler=%s error=%r",
                    event.type,
                    getattr(handler, "__name__", str(handler)),
                    result,
                    exc_info=result,
                )


event_bus = EventBus()
