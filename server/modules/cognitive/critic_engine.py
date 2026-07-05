from __future__ import annotations

from typing import Any
from pathlib import Path
import json
import os
from datetime import datetime, timezone

from common.paths import NERON_DATA_DIR
from modules.cognitive.history import append_jsonl, compact_cognitive_state


CRITIC_HISTORY_PATH = Path(
    os.getenv(
        "NERON_CRITIC_HISTORY_PATH",
        str(NERON_DATA_DIR / "critic_history.jsonl"),
    )
)


class CriticEngine:
    """
    Moteur critique minimal de Néron.
    """

    def evaluate(
        self,
        cognitive_state: dict[str, Any],
    ) -> dict[str, Any]:

        score = 100

        critiques: list[str] = []
        recommendations: list[str] = []

        self_health = cognitive_state.get("self_health")
        world_status = cognitive_state.get("world_status")
        active_tasks = cognitive_state.get(
            "active_tasks",
            [],
        )

        if self_health == "stable_with_warning":
            score -= 15

            critiques.append(
                "Santé interne partiellement dégradée."
            )

            recommendations.append(
                "Analyser les ressources système."
            )

        if self_health == "critical":
            score -= 40

            critiques.append(
                "Santé interne critique."
            )

            recommendations.append(
                "Stabilisation immédiate requise."
            )

        if world_status == "degraded":
            score -= 20

            critiques.append(
                "Environnement externe dégradé."
            )

            recommendations.append(
                "Vérifier les services externes."
            )

        if not active_tasks:
            score -= 10

            critiques.append(
                "Aucune tâche active."
            )

            recommendations.append(
                "Créer des tâches liées à l'objectif actif."
            )

        result = {
            "cognitive_score": max(score, 0),
            "criticisms": critiques,
            "recommendations": recommendations,
        }

        self.save_evaluation(
            cognitive_state,
            result,
        )

        return result

    def evaluate_plan(
        self,
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Évalue le risque d'un plan Planner avant exécution.
        """

        risk_score = 0
        risks: list[str] = []
        recommendations: list[str] = []

        steps = plan.get("steps", [])

        if not steps:
            risk_score += 40
            risks.append("Le plan ne contient aucune étape.")
            recommendations.append("Refuser l'exécution tant que le plan est vide.")

        sensitive_detected = False
        sensitive_actions = {
            "apply_patch",
            "write_file",
            "delete_file",
            "modify_core",
            "modify_system_config",
            "modify_systemd",
            "read_secret",
            "write_secret",
            "modify_secret",
            "modify_security",
            "apply_destructive_change",
        }
        sensitive_keywords = {
            "suppression",
            "supprimer",
            "delete",
            "destructive",
            "destructif",
            "systemd",
            "secret",
            "token",
            "ssh",
            "sécurité",
            "security",
        }

        for step in steps:
            action = step.get("action")
            agent = step.get("agent")
            text = " ".join(
                str(step.get(field) or "")
                for field in ("title", "description", "action", "agent")
            ).lower()

            if action in sensitive_actions:
                sensitive_detected = True
                risk_score += 50
                risks.append(f"Action sensible détectée : {action}.")
                recommendations.append("Bloquer l'exécution automatique.")

            for keyword in sensitive_keywords:
                if keyword in text:
                    sensitive_detected = True
                    risks.append(f"Mot-clé sensible détecté : {keyword}.")

            if agent in {"code_agent", "agent_creator"}:
                risk_score += 15
                risks.append(f"Agent pouvant produire du code : {agent}.")
                recommendations.append("Limiter l'écriture au dossier workspace.")

            if action in {"run_tests", "prepare_tests"}:
                risk_score += 5

        if sensitive_detected:
            risk_score = max(risk_score, 90)

        if plan.get("approval_required") is True and plan.get("approved") is not True:
            risk_score += 20
            risks.append("Le plan n'est pas approuvé.")
            recommendations.append("Demander une approbation avant exécution.")

        risks = list(dict.fromkeys(risks))
        recommendations = list(dict.fromkeys(recommendations))

        if sensitive_detected or risk_score > 80:
            level = "critical"
            execution_allowed = False
        elif risk_score > 30:
            level = "medium"
            execution_allowed = True
        else:
            level = "low"
            execution_allowed = True

        result = {
            "risk_score": min(risk_score, 100),
            "risk_level": level,
            "execution_allowed": execution_allowed,
            "sensitive_action_detected": sensitive_detected,
            "risks": risks,
            "recommendations": recommendations,
        }

        self.save_evaluation(
            {
                "type": "plan_risk",
                "plan_id": plan.get("id"),
                "goal": plan.get("goal"),
            },
            result,
        )

        return result

    def save_evaluation(
        self,
        cognitive_state: dict[str, Any],
        result: dict[str, Any],
    ) -> None:

        CRITIC_HISTORY_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "cognitive_state": compact_cognitive_state(cognitive_state),
            "result": result,
        }

        append_jsonl(CRITIC_HISTORY_PATH, payload)


_critic_engine: CriticEngine | None = None


def get_critic_engine() -> CriticEngine:
    global _critic_engine

    if _critic_engine is None:
        _critic_engine = CriticEngine()

    return _critic_engine
