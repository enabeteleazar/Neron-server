from __future__ import annotations

import logging


def get_service_logger(component: str) -> logging.Logger:
    return logging.getLogger(f"neron.common.{component}")


__all__ = ["get_service_logger"]
