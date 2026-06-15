from __future__ import annotations

AGENT_SPEC = {
    "capabilities": [
        "deterministic_response"
    ],
    "goal": "Créer un agent qui donne la date de Pâques",
    "inputs": [
        "text"
    ],
    "kind": "agent",
    "name": "donne_la_date_agent",
    "outputs": [
        "response"
    ],
    "safety": {
        "filesystem": "limited",
        "network": "none_required"
    },
    "title": "Agent donne_la_date_agent"
}
AGENT_SPEC_SIGNATURE = 'capabilities deterministic response goal creer un agent qui donne la date de paques inputs text kind agent name donne la date agent outputs response safety filesystem limited network none required title agent donne la date agent'


class Agent:
    name = 'donne_la_date_agent'

    async def execute(self, text: str = "") -> dict:
        return {
            "status": "ok",
            "agent": self.name,
            "response": 'Agent disponible pour : Créer un agent qui donne la date de Pâques',
        }
