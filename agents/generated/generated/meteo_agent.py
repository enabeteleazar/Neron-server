from __future__ import annotations


class Agent:
    async def execute(self, text: str = ""):
        return {
            "response": (
                "Agent météo actif.\n"
                "Je suis prêt à récupérer ou analyser la météo, "
                "mais je n’ai pas encore de connecteur météo réel configuré."
            )
        }
