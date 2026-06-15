# Legacy-compatible enriched WorldModel package.
#
# The official runtime WorldModel used by neron-core is
# `modules.world_model.world_model` exposed through `core.api.world_model_routes`.
# This package is retained for the historical builder/store API and tests.
# World Model — API publique

from __future__ import annotations

from .builder import build_world_model
from .store   import WorldModelStore

__all__ = ["build_world_model", "WorldModelStore"]
