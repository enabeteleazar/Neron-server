from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.autonomous.multi_agent_system import (
    MultiAgentSystem,
)

from core.autonomous.watchdog_notifier import (
    WatchdogNotifier,
)

from core.autonomous.learning_memory import (
    LearningMemory,
)


class SupervisorAgent:

    """
    Agent superviseur autonome.

    Rôle :
    - surveiller les objectifs
    - orchestrer les agents
    - relancer les tâches échouées
    - maintenir la cognition continue
    """

    def __init__(self):

        self.watchdog = WatchdogNotifier()

        self.multi_agent = (
            MultiAgentSystem()
        )

        self.memory = (
            LearningMemory()
        )

        self.active_goals: list[dict] = []

    def add_goal(
        self,
        objective: str,
        priority: int = 5,
    ) -> dict:

        goal = {
            "objective": objective,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds"),
        }

        self.active_goals.append(goal)

        self.watchdog.warning(
            "Supervisor",
            f"Nouvel objectif : {objective}",
        )

        return {
            "success": True,
            "goal": goal,
        }

    def run_cycle(self) -> dict[str, Any]:

        self.watchdog.info(
            "Supervisor",
            "Cycle superviseur démarré",
        )

        processed = []

        for goal in self.active_goals:

            if goal["status"] != "pending":
                continue

            result = (
                self.multi_agent.run(
                    goal["objective"]
                )
            )

            success = result.get(
                "success",
                False,
            )

            goal["status"] = (
                "completed"
                if success
                else "failed"
            )

            processed.append(
                {
                    "goal": goal,
                    "result": result,
                }
            )

            self.memory.record_action(
                action="supervisor_goal",
                category="supervisor",
                risk="medium",
                success=success,
                confidence=0.8,
                metadata=goal["objective"],
            )

            if success:

                self.watchdog.info(
                    "Supervisor",
                    (
                        "Objectif terminé : "
                        f"{goal['objective']}"
                    ),
                )

            else:

                self.watchdog.error(
                    "Supervisor",
                    (
                        "Échec objectif : "
                        f"{goal['objective']}"
                    ),
                )

        return {
            "success": True,
            "processed": processed,
            "active_goals": self.active_goals,
        }

    def retry_failed(self) -> dict:

        retried = 0

        for goal in self.active_goals:

            if goal["status"] == "failed":

                goal["status"] = "pending"

                retried += 1

                self.watchdog.warning(
                    "Supervisor",
                    (
                        "Relance objectif : "
                        f"{goal['objective']}"
                    ),
                )

        return {
            "success": True,
            "retried": retried,
        }
