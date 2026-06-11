from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from core.agent_factory.registry import DynamicAgentRegistry, AGENT_REGISTRY

logger = logging.getLogger("neron.runtime.agents")


@dataclass
class AgentRuntimeState:
    name: str
    loaded_at: float = field(default_factory=time.time)
    runs: int = 0
    failures: int = 0
    last_error: str | None = None
    last_execution_ms: float | None = None


class AgentRuntimeManager:
    """
    Gestionnaire central des agents dynamiques générés.
    Version initiale :
    - charge les agents generated
    - liste les agents disponibles
    - exécute un agent par nom
    - garde un état runtime simple
    """

    def __init__(self) -> None:
        self.registry = DynamicAgentRegistry()
        self.states: dict[str, AgentRuntimeState] = {}

    def reload(self) -> dict[str, Any]:
        agents = self.registry.load_generated_agents() or AGENT_REGISTRY

        for name in agents:
            self.states.setdefault(name, AgentRuntimeState(name=name))

        stale = set(self.states) - set(agents)
        for name in stale:
            self.states.pop(name, None)

        logger.info("agents_reloaded count=%s agents=%s", len(agents), sorted(agents))

        return {
            "ok": True,
            "count": len(agents),
            "agents": sorted(agents),
        }

    def list_agents(self) -> list[str]:
        self.reload()
        return sorted(AGENT_REGISTRY.keys())

    def get_state(self, name: str) -> dict[str, Any] | None:
        state = self.states.get(name)
        if not state:
            return None
        return {
            "name": state.name,
            "loaded_at": state.loaded_at,
            "runs": state.runs,
            "failures": state.failures,
            "last_error": state.last_error,
            "last_execution_ms": state.last_execution_ms,
        }

    async def run(self, name: str, text: str = "") -> dict[str, Any]:
        from core.agent_runtime.runtime import AgentRuntime

        self.reload()
        resolved_name = name if name in AGENT_REGISTRY else f"{name}_agent"
        state = self.states.setdefault(resolved_name, AgentRuntimeState(name=resolved_name))
        result = await AgentRuntime(registry=self.registry).run_agent(name, text)
        elapsed = result.duration_ms
        if result.ok:
            state.runs += 1
            state.last_execution_ms = elapsed
            state.last_error = None
            return result.to_dict()

        state.runs += 1
        state.failures += 1
        state.last_error = result.error
        state.last_execution_ms = elapsed
        payload = result.to_dict()
        payload["available"] = sorted(AGENT_REGISTRY.keys())
        return payload


_runtime_manager: AgentRuntimeManager | None = None


def get_agent_runtime_manager() -> AgentRuntimeManager:
    global _runtime_manager
    if _runtime_manager is None:
        _runtime_manager = AgentRuntimeManager()
    return _runtime_manager
