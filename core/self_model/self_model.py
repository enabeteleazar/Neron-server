from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SelfModel:
    started_at: float = field(default_factory=time.time)

    identity: dict[str, Any] = field(default_factory=lambda: {
        "name": "Néron",
        "role": "Assistant IA personnel",
        "language": "fr",
        "version": "0.2.0",
    })

    active_goal: str = "restaurer la boucle cognitive autonome"

    health_realtime: str = "unknown"
    health_historical: str = "unknown"
    health_global: str = "unknown"

    observed_events: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    last_intent: str | None = None
    last_agent: str | None = None
    last_error: str | None = None

    available_agents: list[str] = field(default_factory=list)

    runtime: dict[str, Any] = field(default_factory=dict)

    def collect_runtime(self) -> None:
        self.runtime["uptime_seconds"] = round(time.time() - self.started_at, 2)

        if not self.health_realtime:
            self.health_realtime = "unknown"

        if not self.health_historical:
            self.health_historical = "unknown"

        if self.health_realtime == "warning":
            self.health_global = "stable_with_warning"
        elif self.health_realtime == "critical":
            self.health_global = "critical"
        elif self.health_realtime in {"ok", "healthy", "excellent"}:
            self.health_global = "stable"
        else:
            self.health_global = "unknown"

    def update_from_event(self, event: Any = None, **kwargs: Any) -> None:
        if hasattr(event, "type"):
            event_dict = {
                "type": getattr(event, "type", None),
                "source": getattr(event, "source", None),
                "payload": getattr(event, "payload", {}),
                "details": getattr(event, "details", {}),
                "error": getattr(event, "error", None),
            }
        elif kwargs:
            if event is None:
                event = kwargs
            elif isinstance(event, dict):
                event = {**event, **kwargs}

        if isinstance(event, dict):
            event_dict = event
        else:
            event_dict = {"type": str(event)}

        payload = event_dict.get("payload") or {}
        details = event_dict.get("details") or {}

        normalized_event = {
            "type": event_dict.get("type"),
            "source": event_dict.get("source"),
            "intent": details.get("intent") or payload.get("intent"),
            "agent": details.get("agent") or payload.get("agent"),
            "error": event_dict.get("error") or details.get("error") or payload.get("error"),
        }

        self.observe_event(normalized_event)

    def observe_event(self, event: dict[str, Any]) -> None:
        self.observed_events.append(event)

        if len(self.observed_events) > 100:
            self.observed_events = self.observed_events[-100:]

        intent = event.get("intent")
        agent = event.get("agent")
        error = event.get("error")

        if intent:
            self.last_intent = intent

        if agent:
            self.last_agent = agent

        if error:
            self.last_error = error

    def set_available_agents(self, agents: list[str]) -> None:
        self.available_agents = sorted(set(agents))

    def set_agents_available(self, agents: list[str]) -> None:
        self.set_available_agents(agents)


    def set_agents_available(self, agents: list[str]) -> None:
        self.set_available_agents(agents)

    def update_from_event(self, event: Any = None, **kwargs: Any) -> None:
        if kwargs:
            if event is None:
                event = kwargs
            elif isinstance(event, dict):
                event = {**event, **kwargs}

        if isinstance(event, dict):
            event_dict = event
        else:
            event_dict = {
                "type": getattr(event, "type", None),
                "source": getattr(event, "source", None),
                "payload": getattr(event, "payload", {}),
                "details": getattr(event, "details", {}),
                "error": getattr(event, "error", None),
            }

        payload = event_dict.get("payload") or {}
        details = event_dict.get("details") or {}

        self.observe_event({
            "type": event_dict.get("type"),
            "source": event_dict.get("source"),
            "intent": (
                event_dict.get("intent")
                or details.get("intent")
                or payload.get("intent")
            ),
            "agent": (
                event_dict.get("agent")
                or details.get("agent")
                or payload.get("agent")
            ),
            "error": (
                event_dict.get("error")
                or details.get("error")
                or payload.get("error")
            ),
        })

    def internal_status_text(self) -> str:
        data = self.to_dict()

        uptime = data.get("runtime", {}).get("uptime_seconds", 0)
        events_count = data.get("observed_events_count", 0)
        last_intent = data.get("last_intent") or "aucune"
        last_agent = data.get("last_agent") or "self_model"
        last_error = data.get("last_error") or "aucune"

        agents = data.get("available_agents") or []
        agents_text = ", ".join(agents) if agents else "aucun agent déclaré"

        recent_alerts = len(data.get("diagnostics", []))

        return (
            "État interne de Néron :\n"
            f"- Uptime : {uptime}s\n"
            f"- Événements observés : {events_count}\n"
            f"- Dernière intention : {last_intent}\n"
            f"- Dernier agent : {last_agent}\n"
            f"- Agents disponibles : {agents_text}\n"
            f"- Alertes récentes : {recent_alerts}\n"
            f"- Dernière erreur : {last_error}"
        )

    def set_health(
        self,
        realtime: str | None = None,
        historical: str | None = None,
        global_status: str | None = None,
    ) -> None:
        if realtime:
            self.health_realtime = realtime
        if historical:
            self.health_historical = historical
        if global_status:
            self.health_global = global_status

    def to_dict(self) -> dict[str, Any]:
        self.collect_runtime()

        return {
            "identity": self.identity,
            "active_goal": self.active_goal,
            "health_realtime": self.health_realtime,
            "health_historical": self.health_historical,
            "health_global": self.health_global,
            "observed_events": self.observed_events,
            "observed_events_count": len(self.observed_events),
            "diagnostics": self.diagnostics,
            "recommendations": self.recommendations,
            "last_intent": self.last_intent,
            "last_agent": self.last_agent,
            "last_error": self.last_error,
            "available_agents": self.available_agents,
            "runtime": self.runtime,
            "cognitive_summary": self.build_summary(),
        }


    def summary(self) -> str:
        if hasattr(self, "internal_status_text"):
            return self.internal_status_text()

        data = self.to_dict()
        return data.get("cognitive_summary") or "État interne indisponible."

    def build_summary(self) -> str:
        if self.health_global == "stable_with_warning":
            return "Système stable, mais autonomie cognitive partielle."
        if self.health_global == "stable":
            return "Système stable."
        if self.health_global == "critical":
            return "Système en état critique."
        return "État interne partiellement connu."


_SELF_MODEL = SelfModel()


def get_self_model() -> SelfModel:
    return _SELF_MODEL
