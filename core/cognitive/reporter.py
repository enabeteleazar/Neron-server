from __future__ import annotations

from datetime import datetime
from typing import Any


class CognitiveReporter:
    """
    Génère un rapport lisible de l'état cognitif de Néron.
    """

    def generate_text_report(
        self,
        state: dict[str, Any],
    ) -> str:
        tasks = state.get("active_tasks", [])
        reasoning = state.get("reasoning", {})
        decision = state.get("decision", {})
        execution = state.get("execution_result", {})

        task_lines = "\n".join(
            f"- {task.get('title')} [{task.get('priority')}]"
            for task in tasks
        ) or "- Aucune tâche active"

        criticisms = "\n".join(
            f"- {item}"
            for item in state.get("criticisms", [])
        ) or "- Aucune critique"

        recommendations = "\n".join(
            f"- {item}"
            for item in state.get("recommendations", [])
        ) or "- Aucune recommandation"

        return f"""🧠 RAPPORT COGNITIF NÉRON

Date : {datetime.now().strftime("%Y-%m-%d %H:%M")}

ÉTAT
- Santé interne : {state.get("self_health")}
- État du monde : {state.get("world_status")}
- Score cognitif : {state.get("cognitive_score")}/100

OBJECTIF ACTIF
- {state.get("active_goal")}

TÂCHES ACTIVES
{task_lines}

RAISONNEMENT
- Stratégie : {reasoning.get("strategy")}
- Priorité : {reasoning.get("priority")}
- Confiance : {reasoning.get("confidence")}

DÉCISION
- Action : {decision.get("action")}
- Cible : {decision.get("target")}

EXÉCUTION
- Statut : {execution.get("status")}
- Message : {execution.get("message")}

CRITIQUES
{criticisms}

RECOMMANDATIONS
{recommendations}
"""


_reporter: CognitiveReporter | None = None


def get_cognitive_reporter() -> CognitiveReporter:
    global _reporter

    if _reporter is None:
        _reporter = CognitiveReporter()

    return _reporter
