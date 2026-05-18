from __future__ import annotations

import asyncio
import logging

from core.world_model.world_model import get_world_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

LOGGER = logging.getLogger("neron.world_model.loop")

UPDATE_INTERVAL = 15


async def update_loop() -> None:
    LOGGER.info("world_model_loop_started")

    model = get_world_model()

    while True:
        try:
            model.refresh()
            model.save_state()

            LOGGER.info(
                "world_model_updated status=%s diagnostics=%s",
                model.environment_status,
                len(model.diagnostics),
            )

        except Exception:
            LOGGER.exception("world_model_update_failed")

        await asyncio.sleep(UPDATE_INTERVAL)


async def main() -> None:
    await update_loop()


if __name__ == "__main__":
    asyncio.run(main())
