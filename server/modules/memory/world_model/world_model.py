"""Deprecated import adapter for the canonical World Model.

World state belongs to :mod:`core.world_model`. This module remains importable
for external callers that still use the historical memory namespace.
"""

from modules.world_model.world_model import WorldModel

MemoryWorldModel = WorldModel

__all__ = ["MemoryWorldModel", "WorldModel"]
