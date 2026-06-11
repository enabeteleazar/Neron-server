from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4


CapabilityExecutor = Callable[[str], Awaitable[Any]]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CapabilityRequest:
    text: str
    source: str = "user"
    channel: str = "api"
    request_id: str = field(default_factory=lambda: f"cap_{uuid4().hex}")
    user_id: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CapabilityDecision:
    decision: str
    confidence: float
    reason: str
    capability_type: str | None = None
    selected_tool: str | None = None
    selected_agent: str | None = None
    requires_creation: bool = False
    creation_type: str | None = None
    async_required: bool = False
    human_validation_required: bool = False
    safety_level: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CapabilityResult:
    status: str
    response: str
    async_started: bool = False
    goal_id: str | None = None
    project_id: str | None = None
    agent_slug: str | None = None
    tool_slug: str | None = None
    error: str | None = None
    request_id: str | None = None
    decision: CapabilityDecision | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.decision is not None:
            payload["decision"] = self.decision.to_dict()
        return payload


@dataclass
class Capability:
    slug: str
    name: str
    capability_type: str
    source: str
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    signature: str = ""
    agent_slug: str | None = None
    tool_slug: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    executor: CapabilityExecutor | None = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("executor", None)
        return payload
