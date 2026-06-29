from __future__ import annotations

import asyncio
import signal

from watchdog.runtime import WatchdogRuntime


_stop_event = asyncio.Event()


def _request_stop() -> None:
    _stop_event.set()


async def main() -> None:
    loop = asyncio.get_running_loop()
    runtime = WatchdogRuntime()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _request_stop)

    await runtime.start()

    try:
        await _stop_event.wait()
    finally:
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
