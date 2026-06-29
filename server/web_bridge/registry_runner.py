from __future__ import annotations

import asyncio
import logging
import signal

from server.common.registry.client import RegistryClient


logger = logging.getLogger("web.registry")


def create_registry_client() -> RegistryClient:
    return RegistryClient(
        service_name="web",
        version="0.1.0",
        host="localhost",
        port=8080,
        capabilities=["dashboard", "chat_ui", "monitoring_ui", "admin_ui"],
        metadata={},
    )


async def run(stop_event: asyncio.Event | None = None) -> None:
    event = stop_event or asyncio.Event()
    if stop_event is None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, event.set)

    client = create_registry_client()
    await client.start()
    logger.info("Web Registry sidecar started")
    try:
        await event.wait()
    finally:
        await client.stop()
        logger.info("Web Registry sidecar stopped")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
