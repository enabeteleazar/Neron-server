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
        self.reload()

        agent = AGENT_REGISTRY.get(name) or AGENT_REGISTRY.get(f"{name}_agent")

        if agent is None:
            return {
                "ok": False,
                "error": f"Agent introuvable : {name}",
                "available": sorted(AGENT_REGISTRY.keys()),
            }

        resolved_name = name if name in AGENT_REGISTRY else f"{name}_agent"
        state = self.states.setdefault(resolved_name, AgentRuntimeState(name=resolved_name))

        start = time.monotonic()

        try:
            result = await agent.execute(text=text)
            elapsed = round((time.monotonic() - start) * 1000, 2)

            state.runs += 1
            state.last_execution_ms = elapsed
            state.last_error = None

            if isinstance(result, dict):
                response = result.get("response", str(result))
                raw = result
            elif hasattr(result, "content"):
                response = result.content if getattr(result, "success", True) else f"⚠️ {result.error}"
                raw = {
                    "success": getattr(result, "success", True),
                    "content": getattr(result, "content", None),
                    "error": getattr(result, "error", None),
                }
            else:
                response = str(result)
                raw = {"response": response}

            return {
                "ok": True,
                "agent": resolved_name,
                "response": response,
                "execution_time_ms": elapsed,
                "raw": raw,
            }

        except Exception as exc:
            elapsed = round((time.monotonic() - start) * 1000, 2)

            state.runs += 1
            state.failures += 1
            state.last_error = str(exc)
            state.last_execution_ms = elapsed

            logger.exception("agent_runtime_failed name=%s error=%s", resolved_name, exc)

            return {
                "ok": False,
                "agent": resolved_name,
                "error": str(exc),
                "execution_time_ms": elapsed,
            }


_runtime_manager: AgentRuntimeManager | None = None


def get_agent_runtime_manager() -> AgentRuntimeManager:
    global _runtime_manager
    if _runtime_manager is None:
        _runtime_manager = AgentRuntimeManager()
    return _runtime_manager
