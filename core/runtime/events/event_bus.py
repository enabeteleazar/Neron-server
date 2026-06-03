from collections import defaultdict
from typing import Callable
import inspect

from core.runtime.events.event_logger import log_event


class EventBus:
    def __init__(self):
        self._handlers = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable):
        self._handlers[event_type].append(handler)

    async def emit(self, event_type: str, payload: dict | None = None):
        payload = payload or {}

        log_event(event_type, payload)

        handlers = self._handlers.get(event_type, [])

        results = []

        for handler in handlers:
            if inspect.iscoroutinefunction(handler):
                result = await handler(payload)
            else:
                result = handler(payload)

            results.append(result)

        return results


event_bus = EventBus()
