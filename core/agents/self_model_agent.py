"""
Legacy compatibility module.

This file is currently not referenced by the active agent routing pipeline.
Prefer core.agents.core.self_model_agent for future SelfModel agent wiring.
Do not extend this module; keep it only for backward compatibility until removal.
"""

from __future__ import annotations

from core.self_model.self_model import get_self_model


class SelfModelAgent:

    name = "self_model"

    async def run(self, query: str) -> str:
        model = get_self_model()
        data = model.to_dict()

        uptime = data.get("runtime", {}).get("uptime_seconds", 0)
        events_count = data.get("observed_events_count", 0)

        last_intent = data.get("last_intent") or "aucune"
        last_agent = data.get("last_agent") or "aucun"
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
