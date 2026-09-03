"""Contrats de providers — noyau partage.

Le Coeur (LLM, Memory) et Capabilities implementent ces contrats ; Core les
consomme. Ils vivaient dans `core.providers`, ce qui obligeait le Coeur a
dependre de Core pour parler son propre langage. Extraits en Phase 2F.

`server/common` ne depend d'aucune plateforme : ces modules n'utilisent que
la bibliotheque standard et pydantic.
"""

from .models import (
    ProviderInfo,
    ProviderRequest,
    ProviderResponse,
    ProviderStatus,
    ProviderType,
    utc_now,
)
from .protocol import ProviderProtocol

__all__ = [
    "ProviderInfo",
    "ProviderProtocol",
    "ProviderRequest",
    "ProviderResponse",
    "ProviderStatus",
    "ProviderType",
    "utc_now",
]
