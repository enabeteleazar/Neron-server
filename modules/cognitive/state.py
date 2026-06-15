"""Cognitive state container.

Hold lightweight cognitive state and provide serialization.
"""

from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class CognitiveState:
    """Minimal cognitive state container."""

    state: dict[str, Any] = field(default_factory=dict)
    last_update: float | None = None

    def update(self, patch: dict[str, Any]) -> None:
        self.state.update(patch)
        self.last_update = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {"state": self.state, "last_update": self.last_update}
