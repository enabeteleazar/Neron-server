# core/agents/communication/telegram_agent.py
# DÉPRÉCIÉ — toute la logique a été migrée vers core/gateway/telegram_gateway.py
#
# Ce module est conservé pour rétrocompatibilité uniquement.
# N'importe pas directement : utilise core.gateway.telegram_gateway.TelegramGateway.

import warnings

warnings.warn(
    "telegram_agent est déprécié. "
    "Utilise core.gateway.telegram_gateway.TelegramGateway à la place.",
    DeprecationWarning,
    stacklevel=2,
)

from core.gateway.telegram_gateway import TelegramGateway  # noqa: F401

# Compat aliases (ancienne API fonctionnelle)
from core.gateway.telegram_gateway import TelegramGateway as _gw

_instance: TelegramGateway | None = None


def _get_instance() -> TelegramGateway:
    global _instance
    if _instance is None:
        _instance = TelegramGateway()
    return _instance


async def start_bot() -> None:
    await _get_instance().start()


async def stop_bot() -> None:
    await _get_instance().stop()


async def send_notification(message: str, level: str = "info") -> None:
    await _get_instance().send_notification(message, level)


def set_agents(agents: dict) -> None:
    _get_instance().set_agents(agents)
