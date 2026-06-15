from __future__ import annotations

AGENT_SPEC = {
    "capabilities": [
        "deterministic_response"
    ],
    "goal": "Créer un agent nommé easter_2027_agent_v3 qui répond exactement à la date de Pâques 2027",
    "inputs": [
        "text"
    ],
    "kind": "agent",
    "name": "easter_2027_agent_v3",
    "outputs": [
        "response"
    ],
    "safety": {
        "filesystem": "limited",
        "network": "none_required"
    },
    "title": "Agent easter_2027_agent_v3"
}
AGENT_SPEC_SIGNATURE = 'capabilities deterministic response goal creer un agent nomme easter 2027 agent v3 qui repond exactement a la date de paques 2027 inputs text kind agent name easter 2027 agent v3 outputs response safety filesystem limited network none required title agent easter 2027 agent v3'


class Agent:
    name = 'easter_2027_agent_v3'

    async def execute(self, text: str = "") -> dict:
        return {
            "status": "ok",
            "agent": self.name,
            "date": "2027-03-28",
            "response": "Pâques 2027 tombe le 28 mars 2027.",
        }
