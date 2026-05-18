from __future__ import annotations

import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | neron.cognitive_loop | %(message)s",
)

logger = logging.getLogger("neron.cognitive_loop")


def main() -> None:
    logger.info("CognitiveLoop démarrée")

    while True:
        logger.info("[CognitiveLoop] cycle actif")
        time.sleep(10)


if __name__ == "__main__":
    main()
