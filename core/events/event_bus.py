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
        logger.info(
            "event_published type=%s source=%s event_id=%s handlers=%s",
            event.type,
            event.source,
            event.event_id,
            len(handlers),
        )

        if not handlers:
            return

        results = await asyncio.gather(
            *(handler(event) for handler in handlers),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.exception("event_handler_failed type=%s error=%s", event.type, result)


event_bus = EventBus()
