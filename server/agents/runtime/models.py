from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from tools.models import ToolResult, ToolSpec
from tools.runtime import ToolRuntime


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ToolBinding:
    slug: str
    spec: ToolSpec
    runtime: ToolRuntime = field(repr=False, compare=False)

    async def execute(self, payload: dict[str, Any] | None = None) -> ToolResult:
        return await self.runtime.execute_tool(self.slug, payload or {})

    def to_dict(self) -> dict[str, Any]:
        return {"slug": self.slug, "spec": self.spec.to_dict()}


@dataclass
class ExecutionContext:
    request: str
    execution_id: str = field(
        default_factory=lambda: f"agent_exec_{uuid4().hex}"
    )
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, ToolBinding] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    async def run_tool(
        self,
        slug: str,
        payload: dict[str, Any] | None = None,
    ) -> ToolResult:
        binding = self.tools.get(slug)
        if binding is None:
            return ToolResult(ok=False, error=f"tool_not_bound:{slug}")
        return await binding.execute(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "request": self.request,
            "context": self.context,
            "metadata": self.metadata,
            "tools": sorted(self.tools),
            "created_at": self.created_at,
        }


@dataclass
class AgentInstance:
    agent_slug: str
    agent: Any = field(default=None, repr=False, compare=False)
    path: str = ""
    spec: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, ToolBinding] = field(default_factory=dict)
    loaded_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_slug": self.agent_slug,
            "path": self.path,
            "spec": self.spec,
            "tools": {
                slug: binding.to_dict() for slug, binding in self.tools.items()
            },
            "loaded_at": self.loaded_at,
        }


@dataclass
class AgentExecutionResult:
    execution_id: str
    agent_slug: str
    status: str
    response: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: float | None = None
    sandbox_used: bool = False
    sandbox_backend: str | None = None
    sandbox_isolation: str | None = None
    sudo_used: bool = False

    @property
    def ok(self) -> bool:
        return self.status == "completed" and self.error is None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ok"] = self.ok
        payload["agent"] = self.agent_slug
        payload["execution_time_ms"] = self.duration_ms
        payload["raw"] = self.result
        return payload
