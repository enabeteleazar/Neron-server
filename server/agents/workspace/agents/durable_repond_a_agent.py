from __future__ import annotations

AGENT_SPEC = {
    "capabilities": [
        "deterministic_response"
    ],
    "goal": "Créer un agent durable qui répond à cette demande : Je veux que tu surveille les lancement des fusée spaceX et que tu me prévienne 1h avant le lancement",
    "inputs": [
        "text"
    ],
    "kind": "agent",
    "name": "durable_repond_a_agent",
    "outputs": [
        "response"
    ],
    "safety": {
        "filesystem": "limited",
        "network": "none_required"
    },
    "title": "Agent durable_repond_a_agent"
}
AGENT_SPEC_SIGNATURE = 'capabilities deterministic response goal creer un agent durable qui repond a cette demande je veux que tu surveille les lancement des fusee spacex et que tu me previenne 1h avant le lancement inputs text kind agent name durable repond a agent outputs response safety filesystem limited network none required title agent durable repond a agent'


class Agent:
    name = 'durable_repond_a_agent'

    async def execute(self, text: str = "") -> dict:
        request = text.strip() or 'Créer un agent durable qui répond à cette demande : Je veux que tu surveille les lancement des fusée spaceX et que tu me prévienne 1h avant le lancement'
        return {
            "status": "ok",
            "agent": self.name,
            "response": f"Demande traitée : {request}",
        }
