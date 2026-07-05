from __future__ import annotations

from datetime import datetime

from common.paths import NERON_ROOT
from agents.autonomous.action_registry import ActionRegistry
from agents.autonomous.reasoning_agent import ReasoningAgent

from core.autonomous.execution_logger import ExecutionLogger
from core.autonomous.sandbox import Sandbox
from modules.autonomous.scheduler import AutonomousScheduler


class ExecutorAgent:

    def __init__(self):

        self.scheduler = AutonomousScheduler()

        self.registry = ActionRegistry()

        self.logger = ExecutionLogger()

        self.reasoning = ReasoningAgent()

        self.sandbox = Sandbox()

        self._register_default_actions()

    # ─────────────────────────────

    def _register_default_actions(self):

        self.registry.register(
            "memory.semantic_search",
            self._memory_search,
        )

        self.registry.register(
            "system.disk_usage",
            self._disk_usage,
        )

        self.registry.register(
            "system.git_pull",
            self._git_pull,
        )

    # ─────────────────────────────

    def execute_task(
        self,
        task_id: int,
    ) -> dict:

        task = self.scheduler.get_task(task_id)

        if not task:
            raise ValueError(
                f"Tâche introuvable: {task_id}"
            )

        objective = task["objective"]

        self.logger.info(
            task_id,
            f"Démarrage exécution : {objective}",
        )

        self.scheduler.update_task_status(
            task_id,
            "running",
        )

        decision = self.reasoning.decide(
            objective
        )

        self.logger.info(
            task_id,
            f"Reasoning : {decision}",
        )

        if not decision["success"]:

            self.scheduler.update_task_status(
                task_id,
                "failed",
            )

            self.logger.error(
                task_id,
                "Aucune action compatible.",
            )

            return {
                "success": False,
                "task_id": task_id,
                "error": "No action found",
            }

        action_name = decision["action"]

        requires_validation = decision[
            "requires_validation"
        ]

        if requires_validation:

            self.scheduler.update_task_status(
                task_id,
                "waiting_validation",
            )

            self.logger.info(
                task_id,
                (
                    "Validation humaine requise."
                ),
            )

            return {
                "success": False,
                "task_id": task_id,
                "status": "waiting_validation",
                "decision": decision,
            }

        handler = self.registry.get(
            action_name
        )

        self.logger.info(
            task_id,
            f"Action sélectionnée : {action_name}",
        )

        result = handler(objective)

        self.logger.info(
            task_id,
            f"Résultat action : {result}",
        )

        self.scheduler.update_task_status(
            task_id,
            "done",
        )

        self.scheduler.update_last_run(
            task_id,
            datetime.utcnow().isoformat(),
        )

        self.logger.info(
            task_id,
            "Tâche terminée avec succès",
        )

        return {
            "success": True,
            "task_id": task_id,
            "objective": objective,
            "action": action_name,
            "decision": decision,
            "result": result,
            "executed_at": datetime.utcnow().isoformat(),
        }

    # ─────────────────────────────
    # ACTIONS
    # ─────────────────────────────

    def _memory_search(
        self,
        objective: str,
    ) -> dict:

        return {
            "success": True,
            "type": "memory_search",
            "query": objective,
            "result": (
                f"Recherche mémoire simulée : "
                f"{objective}"
            ),
        }

    def _disk_usage(
        self,
        objective: str,
    ) -> dict:

        return self.sandbox.execute(
            "df -h"
        )

    def _git_pull(
        self,
        objective: str,
    ) -> dict:

        return self.sandbox.execute(
            f"cd {NERON_ROOT} && git pull"
        )
