import logging


def get_service_logger(component: str) -> logging.Logger:
    return logging.getLogger(f"neron.common.{component}")
