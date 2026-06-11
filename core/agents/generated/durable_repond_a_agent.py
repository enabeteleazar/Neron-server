from __future__ import annotations

AGENT_SPEC = {
    "capabilities": [
        "deterministic_response"
    ],
    "goal": "Créer un agent durable qui répond à cette demande : Analyse automatiquement les logs Néron et résume les erreurs critiques",
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
AGENT_SPEC_SIGNATURE = 'capabilities deterministic response goal creer un agent durable qui repond a cette demande analyse automatiquement les logs neron et resume les erreurs critiques inputs text kind agent name durable repond a agent outputs response safety filesystem limited network none required title agent durable repond a agent'

import re


ERROR_PATTERN = re.compile(
    r"\b(ERROR|CRITICAL|FATAL|Traceback|Exception)\b",
    re.IGNORECASE,
)


class Agent:
    name = 'durable_repond_a_agent'

    async def execute(self, text: str = "") -> dict:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        errors = [line for line in lines if ERROR_PATTERN.search(line)]
        if not errors:
            response = "Analyse des logs Néron : aucune erreur critique détectée."
        else:
            severity = "CRITICAL" if any(
                token in line.upper()
                for line in errors
                for token in ("CRITICAL", "FATAL")
            ) else "ERROR"
            excerpt = errors[0][:180]
            response = (
                f"Analyse des logs Néron : {len(errors)} erreur(s), "
                f"gravité {severity}. Extrait : {excerpt}. "
                "Recommandation : vérifier le composant concerné."
            )
        return {
            "status": "ok",
            "agent": self.name,
            "response": response,
            "error_count": len(errors),
        }
