from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class MemoryCache:
    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, CacheEntry[object]] = {}

    def get(self, key: str) -> object | None:
        entry = self._items.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: object, ttl_seconds: float | None = None) -> None:
        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        self._items[key] = CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    def invalidate(self, key: str | None = None) -> None:
        if key is None:
            self._items.clear()
            return
        self._items.pop(key, None)
