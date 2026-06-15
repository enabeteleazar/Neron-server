from __future__ import annotations

AGENT_SPEC = {
    "capabilities": [
        "parse_weather_request",
        "static_weather_fallback"
    ],
    "goal": "Repondre aux demandes meteo simples",
    "inputs": [
        "location"
    ],
    "kind": "agent",
    "name": "weather_watch_agent",
    "outputs": [
        "summary",
        "source"
    ],
    "safety": {
        "filesystem": "limited",
        "network": "read_only_if_available"
    },
    "title": "Agent de suivi meteo"
}
AGENT_SPEC_SIGNATURE = 'capabilities parse weather request static weather fallback goal repondre aux demandes meteo simples inputs location kind agent name weather watch agent outputs summary source safety filesystem limited network read only if available title agent de suivi meteo'


class Agent:
    name = "weather_watch_agent"

    async def execute(self, text: str = "") -> dict:
        return {
            "status": "ok",
            "agent": self.name,
            "source": "static_fallback",
            "response": "Agent météo disponible. Connecteur météo externe non configuré; réponse fallback active.",
        }
