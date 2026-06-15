from __future__ import annotations

AGENT_SPEC = {
    "capabilities": [
        "deterministic_response"
    ],
    "goal": "Créer un agent nommé goal_engine_test_agent qui répond goal engine OK",
    "inputs": [
        "text"
    ],
    "kind": "agent",
    "name": "goal_engine_test_agent",
    "outputs": [
        "response"
    ],
    "safety": {
        "filesystem": "limited",
        "network": "none_required"
    },
    "title": "Agent goal_engine_test_agent"
}
AGENT_SPEC_SIGNATURE = 'capabilities deterministic response goal creer un agent nomme goal engine test agent qui repond goal engine ok inputs text kind agent name goal engine test agent outputs response safety filesystem limited network none required title agent goal engine test agent'


class Agent:
    name = 'goal_engine_test_agent'

    async def execute(self, text: str = "") -> dict:
        request = text.strip() or 'Créer un agent nommé goal_engine_test_agent qui répond goal engine OK'
        return {
            "status": "ok",
            "agent": self.name,
            "response": f"Demande traitée : {request}",
        }
