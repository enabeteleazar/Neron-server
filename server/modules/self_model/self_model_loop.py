from __future__ import annotations

import asyncio
import logging

from core.modules.self_model import get_self_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

LOGGER = logging.getLogger("neron.self_model.loop")
UPDATE_INTERVAL = 5


async def update_loop() -> None:
    LOGGER.info("self_model_loop_started")

    model = get_self_model()

    while True:
        try:
            model.refresh()
            model.save_state()

            LOGGER.info(
                "self_model_updated health=%s cpu=%s ram=%s",
                model.health_global,
                model.runtime.get("cpu_usage"),
                model.runtime.get("ram_usage"),
            )

        except Exception:
            LOGGER.exception("self_model_update_failed")

        await asyncio.sleep(UPDATE_INTERVAL)


async def main() -> None:
    await update_loop()


if __name__ == "__main__":
    asyncio.run(main())
