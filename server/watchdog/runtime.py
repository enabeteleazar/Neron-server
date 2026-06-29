from __future__ import annotations

import logging
import time

from agents.builtin.automation.watchdog_agent import (
    start_watchdog,
    stop_watchdog,
)
from server.common.registry.client import RegistryClient


logger = logging.getLogger("watchdog.runtime")


def create_registry_client() -> RegistryClient:
    return RegistryClient(
        service_name="watchdog",
        version="0.1.0",
        host="localhost",
        port=8050,
        capabilities=["monitoring", "alerts", "service_supervision"],
        metadata={},
    )


class WatchdogRuntime:
    """Owns the Watchdog worker and its Core Registry lifecycle."""

    def __init__(self) -> None:
        self.registry_client = create_registry_client()
        self.started_at: float | None = None
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        await start_watchdog()
        await self.registry_client.start()
        self.started_at = time.monotonic()
        self._started = True
        logger.info("Watchdog runtime started")

    async def stop(self) -> None:
        if not self._started:
            await self.registry_client.stop()
            return
        try:
            await self.registry_client.stop()
        finally:
            await stop_watchdog()
            self._started = False
            logger.info("Watchdog runtime stopped")

    @property
    def uptime(self) -> float:
        if self.started_at is None:
            return 0.0
        return max(0.0, time.monotonic() - self.started_at)
