from __future__ import annotations

from typing import Any


def diagnose_alert(payload: dict[str, Any]) -> dict[str, Any]:
    reason = payload.get("reason")
    agent = payload.get("agent")
    execution_time_ms = payload.get("execution_time_ms")

    if reason == "agent_execution_slow":
        return {
            "kind": "performance",
            "severity": "medium",
            "summary": f"L’agent {agent} est lent.",
            "probable_causes": [
                "modèle LLM trop lent",
                "charge CPU/RAM élevée",
                "timeout trop permissif",
                "seuil d’alerte trop bas pour cet agent",
            ],
            "safe_actions": [
                "vérifier CPU/RAM",
                "consulter les derniers événements",
                "adapter le seuil de lenteur par agent",
                "utiliser un modèle plus léger",
            ],
            "metadata": {
                "agent": agent,
                "execution_time_ms": execution_time_ms,
            },
        }

    if reason == "agent_execution_failed":
        return {
            "kind": "failure",
            "severity": "high",
            "summary": f"L’agent {agent} a échoué.",
            "probable_causes": [
                "exception Python",
                "mauvaise configuration",
                "dépendance absente",
                "réponse LLM invalide",
            ],
            "safe_actions": [
                "lire les logs de l’agent",
                "analyser l’erreur",
                "corriger dans workspace",
                "tester avant validation",
            ],
            "metadata": {
                "agent": agent,
            },
        }

    if reason == "agent_instability":
        return {
            "kind": "stability",
            "severity": "high",
            "summary": f"L’agent {agent} semble instable.",
            "probable_causes": [
                "échecs répétés",
                "bug intermittent",
                "ressource externe indisponible",
            ],
            "safe_actions": [
                "désactiver temporairement l’agent",
                "lancer un audit",
                "corriger en workspace",
            ],
            "metadata": payload,
        }

    return {
        "kind": "unknown",
        "severity": "low",
        "summary": f"Alerte non reconnue : {reason}",
        "probable_causes": ["cause inconnue"],
        "safe_actions": ["inspection manuelle recommandée"],
        "metadata": payload,
    }
