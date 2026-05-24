from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


ACTION_HISTORY_PATH = Path(
    "/etc/neron/data/action_history.jsonl"
)


class ActionExecutor:
    """
    ActionExecutor minimal de Néron.

    Transforme une décision cognitive en résultat d'exécution.
    Version prudente : aucune modification système réelle.
    """

    def execute(
        self,
        decision: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        action = decision.get("action")
        target = decision.get("target")
        priority = decision.get("priority", "medium")

        runtime_policy = (context or {}).get("runtime_policy", {}) or {}
        runtime_mode = runtime_policy.get("runtime_mode", "normal")
        autonomous_actions_allowed = runtime_policy.get(
            "autonomous_actions_allowed",
            True,
        )
        heavy_reasoning_allowed = runtime_policy.get(
            "heavy_reasoning_allowed",
            True,
        )

        critical_actions = {
            "continue_monitoring",
            "analyze_system_resources",
        }

        heavy_actions = {
            "generate_task_plan",
            "analyze_world_state",
        }

        if not autonomous_actions_allowed and action not in critical_actions:
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "target": target,
                "priority": priority,
                "status": "blocked",
                "message": "Action bloquée par RuntimeGovernor : actions autonomes désactivées.",
                "runtime_mode": runtime_mode,
                "runtime_policy": runtime_policy,
            }

            self._save_execution(result)
            return result

        if not heavy_reasoning_allowed and action in heavy_actions:
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "target": target,
                "priority": priority,
                "status": "blocked",
                "message": "Action bloquée par RuntimeGovernor : raisonnement lourd désactivé.",
                "runtime_mode": runtime_mode,
                "runtime_policy": runtime_policy,
            }

            self._save_execution(result)
            return result

        status = "noop"
        message = "Aucune action exécutée."

        if action == "analyze_system_resources":
            status = "success"
            message = "Analyse des ressources système demandée via SelfModel."

        elif action == "analyze_world_state":
            status = "success"
            message = "Analyse de l'état du monde demandée via WorldModel."

        elif action == "restore_active_goal":
            status = "success"
            message = "Restauration de l'objectif actif demandée via GoalSystem."

        elif action == "generate_task_plan":
            status = "success"
            message = "Génération de plan demandée via Planner."

        elif action == "continue_monitoring":
            status = "success"
            message = "Surveillance cognitive poursuivie."

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "target": target,
            "priority": priority,
            "status": status,
            "message": message,
            "runtime_mode": runtime_mode,
            "runtime_policy": runtime_policy,
        }

        self._save_execution(
            result
        )

        return result

    def _save_execution(
        self,
        payload: dict[str, Any],
    ) -> None:

        ACTION_HISTORY_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with ACTION_HISTORY_PATH.open(
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


_action_executor: ActionExecutor | None = None


def get_action_executor() -> ActionExecutor:
    global _action_executor

    if _action_executor is None:
        _action_executor = ActionExecutor()

    return _action_executor
