from __future__ import annotations

from typing import Any


class Reasoner:
    """
    Reasoner minimal de Néron.

    Rôle :
    - analyser l'état cognitif
    - choisir une stratégie
    - expliquer pourquoi cette stratégie est choisie
    - fournir une priorité d'action
    """

    def reason(
        self,
        cognitive_state: dict[str, Any],
    ) -> dict[str, Any]:

        self_health = cognitive_state.get("self_health")
        world_status = cognitive_state.get("world_status")
        active_goal = cognitive_state.get("active_goal")
        active_tasks = cognitive_state.get("active_tasks", [])
        cognitive_score = cognitive_state.get("cognitive_score", 100)

        strategy = "continue_current_plan"
        priority = "medium"
        confidence = "medium"
        reasons: list[str] = []

        if self_health in {"critical"}:
            strategy = "stabilize_self"
            priority = "critical"
            confidence = "high"
            reasons.append("La santé interne est critique.")

        elif self_health in {"warning", "stable_with_warning", "unknown"}:
            strategy = "stabilize_self"
            priority = "high"
            confidence = "high"
            reasons.append("La santé interne nécessite une stabilisation.")

        if world_status in {"degraded", "unknown"}:
            strategy = "stabilize_environment"
            priority = "high"
            confidence = "high"
            reasons.append("L'environnement externe n'est pas stable.")

        if not active_goal:
            strategy = "restore_goal"
            priority = "high"
            confidence = "high"
            reasons.append("Aucun objectif actif n'est disponible.")

        if not active_tasks:
            strategy = "create_tasks"
            priority = "medium"
            confidence = "medium"
            reasons.append("Aucune tâche active n'est disponible.")

        if isinstance(cognitive_score, int) and cognitive_score < 60:
            priority = "critical"
            confidence = "high"
            reasons.append("Le score cognitif est faible.")

        elif isinstance(cognitive_score, int) and cognitive_score < 80:
            priority = "high"
            reasons.append("Le score cognitif est moyen.")

        if not reasons:
            reasons.append("L'état cognitif est suffisamment stable pour continuer le plan courant.")

        return {
            "strategy": strategy,
            "priority": priority,
            "confidence": confidence,
            "reasons": reasons,
        }


_reasoner: Reasoner | None = None


def get_reasoner() -> Reasoner:
    global _reasoner

    if _reasoner is None:
        _reasoner = Reasoner()

    return _reasoner
