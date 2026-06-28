from __future__ import annotations

import asyncio
import signal

from agents.builtin.automation.watchdog_agent import (
    start_watchdog,
    stop_watchdog,
)


_stop_event = asyncio.Event()


def _request_stop() -> None:
    _stop_event.set()


async def main() -> None:
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _request_stop)

    await start_watchdog()

    try:
        await _stop_event.wait()
    finally:
        await stop_watchdog()


if __name__ == "__main__":
    asyncio.run(main())
