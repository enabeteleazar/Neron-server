from __future__ import annotations

from typing import Any
from pathlib import Path
import json
from datetime import datetime, timezone


CRITIC_HISTORY_PATH = Path("/etc/neron/data/critic_history.jsonl")


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
            "cognitive_state": cognitive_state,
            "result": result,
        }

        with CRITIC_HISTORY_PATH.open(
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                )
                + "\n"
            )


_critic_engine: CriticEngine | None = None


def get_critic_engine() -> CriticEngine:
    global _critic_engine

    if _critic_engine is None:
        _critic_engine = CriticEngine()

    return _critic_engine
