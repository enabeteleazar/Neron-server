from __future__ import annotations

from typing import Any


def propose_repair(diagnostic: dict[str, Any]) -> dict[str, Any]:
    kind = diagnostic.get("kind")
    agent = diagnostic.get("metadata", {}).get("agent")

    if kind == "performance" and agent == "code_agent":
        return {
            "title": "Adapter le seuil de lenteur du code_agent",
            "risk": "low",
            "requires_human_approval": True,
            "proposed_steps": [
                "créer un seuil spécifique pour code_agent",
                "laisser les autres agents à 10s",
                "mettre code_agent à 60s ou 90s",
                "tester avec une génération de code",
            ],
            "target": "core/events/analyzer.py",
        }

    if kind == "failure":
        return {
            "title": f"Analyser l’échec de {agent}",
            "risk": "medium",
            "requires_human_approval": True,
            "proposed_steps": [
                "extraire les derniers événements de cet agent",
                "lire les logs associés",
                "proposer une correction dans workspace",
                "tester avant promotion",
            ],
            "target": agent,
        }

    return {
        "title": "Inspection manuelle recommandée",
        "risk": "low",
        "requires_human_approval": True,
        "proposed_steps": diagnostic.get("safe_actions", []),
        "target": diagnostic.get("metadata", {}).get("agent"),
    }
