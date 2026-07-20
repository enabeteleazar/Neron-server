from __future__ import annotations

import logging
import os

_logger = logging.getLogger("neron.common.config")


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        _logger.warning(
            "Valeur invalide pour %s=%r — repli sur le défaut %s", name, raw, default
        )
        return default


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        _logger.warning(
            "Valeur invalide pour %s=%r — repli sur le défaut %s", name, raw, default
        )
        return default
