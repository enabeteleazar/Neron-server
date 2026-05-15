from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SelfModelState:
    started_at: float = field(default_factory=time.time)
    events_seen: int = 0
    last_event_type: str | None = None
    last_event_at: str | None = None

    agents_available: list[str] = field(default_factory=list)
    agents_runs: dict[str, int] = field(default_factory=dict)
    agents_failures: dict[str, int] = field(default_factory=dict)

    last_intent: str | None = None
    last_agent: str | None = None
    last_error: str | None = None
    alerts: list[dict[str, Any]] = field(default_factory=list)

    capabilities: list[str] = field(default_factory=lambda: [
        "input_text",
        "intent_routing",
        "agent_routing",
        "dynamic_agents",
        "event_bus",
        "event_persistence",
        "event_analyzer",
        "obsidian_memory",
        "code_generation",
        "agent_runtime",
    ])


class SelfModel:
    def __init__(self) -> None:
        self.state = SelfModelState()

    def update_from_event(self, event_type: str, payload: dict[str, Any], created_at: str) -> None:
        self.state.events_seen += 1
        self.state.last_event_type = event_type
        self.state.last_event_at = created_at

        if event_type == "intent.detected":
            self.state.last_intent = payload.get("intent")

        elif event_type == "agent.selected":
            self.state.last_agent = payload.get("agent")

        elif event_type == "agent.executed":
            agent = payload.get("agent")
            success = payload.get("success")

            if agent:
                self.state.agents_runs[agent] = self.state.agents_runs.get(agent, 0) + 1

                if success is False:
                    self.state.agents_failures[agent] = self.state.agents_failures.get(agent, 0) + 1
                    self.state.last_error = f"Échec agent : {agent}"

        elif event_type == "system.alert":
            alert = dict(payload)
            alert["created_at"] = created_at
            self.state.alerts.append(alert)
            self.state.alerts = self.state.alerts[-20:]
            self.state.last_error = payload.get("reason")

    def set_agents_available(self, agents: list[str]) -> None:
        self.state.agents_available = sorted(agents)

    def to_dict(self) -> dict[str, Any]:
        uptime = round(time.time() - self.state.started_at, 2)

        return {
            "uptime_seconds": uptime,
            "events_seen": self.state.events_seen,
            "last_event_type": self.state.last_event_type,
            "last_event_at": self.state.last_event_at,
            "last_intent": self.state.last_intent,
            "last_agent": self.state.last_agent,
            "last_error": self.state.last_error,
            "agents_available": self.state.agents_available,
            "agents_runs": self.state.agents_runs,
            "agents_failures": self.state.agents_failures,
            "alerts_count": len(self.state.alerts),
            "recent_alerts": self.state.alerts[-5:],
            "capabilities": self.state.capabilities,
        }

    def summary(self) -> str:
        data = self.to_dict()

        agents = ", ".join(data["agents_available"]) or "aucun"
        last_error = data["last_error"] or "aucune"

        return (
            "État interne de Néron :\n"
            f"- Uptime : {data['uptime_seconds']}s\n"
            f"- Événements observés : {data['events_seen']}\n"
            f"- Dernière intention : {data['last_intent']}\n"
            f"- Dernier agent : {data['last_agent']}\n"
            f"- Agents disponibles : {agents}\n"
            f"- Alertes récentes : {data['alerts_count']}\n"
            f"- Dernière erreur : {last_error}"
        )


_self_model: SelfModel | None = None


def get_self_model() -> SelfModel:
    global _self_model
    if _self_model is None:
        _self_model = SelfModel()
    return _self_model
