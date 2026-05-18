from __future__ import annotations

from typing import Any


class DecisionEngine:
    """
    Decision Engine minimal de Néron.

    Transforme une stratégie cognitive
    en action concrète exécutable.
    """

    def decide(
        self,
        reasoning: dict[str, Any],
    ) -> dict[str, Any]:

        strategy = reasoning.get(
            "strategy",
            "continue_current_plan",
        )

        priority = reasoning.get(
            "priority",
            "medium",
        )

        confidence = reasoning.get(
            "confidence",
            "medium",
        )

        action = "continue_monitoring"
        target = "cognitive_core"

        if strategy == "stabilize_self":
            action = "analyze_system_resources"
            target = "self_model"

        elif strategy == "stabilize_environment":
            action = "analyze_world_state"
            target = "world_model"

        elif strategy == "restore_goal":
            action = "restore_active_goal"
            target = "goal_system"

        elif strategy == "create_tasks":
            action = "generate_task_plan"
            target = "planner"

        elif strategy == "continue_current_plan":
            action = "continue_monitoring"
            target = "cognitive_core"

        return {
            "action": action,
            "target": target,
            "priority": priority,
            "confidence": confidence,
        }


_decision_engine: DecisionEngine | None = None


def get_decision_engine() -> DecisionEngine:
    global _decision_engine

    if _decision_engine is None:
        _decision_engine = DecisionEngine()

    return _decision_engine
