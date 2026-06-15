from __future__ import annotations

import asyncio
import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from modules.events.event import Event

logger = logging.getLogger("neron.events")

Handler = Callable[[Event], Awaitable[Any] | Any]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._background_tasks: set[asyncio.Task[None]] = set()

    def subscribe(self, event_type: str, handler: Handler) -> None:
        if handler in self._subscribers[event_type]:
            return
        self._subscribers[event_type].append(handler)
        logger.debug("event_subscribed type=%s handler=%s", event_type, getattr(handler, "__name__", str(handler)))

    def unsubscribe(self, event_type: str, handler: Handler) -> bool:
        handlers = self._subscribers.get(event_type)
        if not handlers or handler not in handlers:
            return False
        handlers.remove(handler)
        if not handlers:
            self._subscribers.pop(event_type, None)
        return True

    async def _dispatch(self, event: Event, handler: Handler) -> Any:
        result = handler(event)
        if inspect.isawaitable(result):
            return await result
        return result

    async def publish(self, event: Event) -> None:
        handlers = list(self._subscribers.get(event.type, []))
        if event.type != "*":
            for handler in self._subscribers.get("*", []):
                if handler not in handlers:
                    handlers.append(handler)
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
            *(self._dispatch(event, handler) for handler in handlers),
            return_exceptions=True,
        )

        for handler, result in zip(handlers, results):
            if isinstance(result, BaseException):
                logger.error(
                    "event_handler_failed type=%s handler=%s error=%r",
                    event.type,
                    getattr(handler, "__name__", str(handler)),
                    result,
                    exc_info=result,
                )

    def publish_background(self, event: Event) -> None:
        """Publish from synchronous producers without coupling their success to listeners."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.publish(event))
            return

        task = loop.create_task(self.publish(event))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        task.add_done_callback(self._log_background_failure)

    @staticmethod
    def _log_background_failure(task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error("event_background_publish_failed error=%r", error, exc_info=error)


event_bus = EventBus()
