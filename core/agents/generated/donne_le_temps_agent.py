from __future__ import annotations

from collections.abc import Callable
from datetime import date

AGENT_SPEC = {
    "capabilities": [
        "deterministic_response"
    ],
    "goal": "Crée un agent qui donne le temps restant avant Noël",
    "inputs": [
        "text"
    ],
    "kind": "agent",
    "name": "donne_le_temps_agent",
    "outputs": [
        "response"
    ],
    "safety": {
        "filesystem": "limited",
        "network": "none_required"
    },
    "title": "Agent donne_le_temps_agent"
}
AGENT_SPEC_SIGNATURE = 'capabilities deterministic response goal cree un agent qui donne le temps restant avant noel inputs text kind agent name donne le temps agent outputs response safety filesystem limited network none required title agent donne le temps agent'


class Agent:
    name = 'donne_le_temps_agent'

    def __init__(self, today: Callable[[], date] | None = None) -> None:
        self._today = today or date.today

    async def execute(self, text: str = "") -> dict:
        current_date = self._today()
        christmas = date(current_date.year, 12, 25)

        if current_date > christmas:
            christmas = date(current_date.year + 1, 12, 25)

        days_remaining = (christmas - current_date).days
        if days_remaining == 0:
            response = "C'est Noël aujourd'hui ! Temps restant : 0 jour."
        else:
            unit = "jour" if days_remaining == 1 else "jours"
            response = (
                f"Il reste {days_remaining} {unit} avant Noël "
                f"({christmas.strftime('%d/%m/%Y')})."
            )

        return {
            "status": "ok",
            "agent": self.name,
            "response": response,
        }
