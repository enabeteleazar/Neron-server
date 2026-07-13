from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


HAStatus = Literal["healthy", "degraded", "unavailable"]


@dataclass(frozen=True)
class HAState:
    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)
    last_changed: str | None = None
    last_updated: str | None = None

    @property
    def domain(self) -> str:
        return self.entity_id.split(".", 1)[0]

    @property
    def friendly_name(self) -> str:
        return str(self.attributes.get("friendly_name") or self.entity_id)


@dataclass(frozen=True)
class HAMatch:
    entity_id: str
    score: float
    name: str
    domain: str
    state: str | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HACommand:
    action: str
    query: str
    entity_id: str | None = None
    domain: str | None = None
    service: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
