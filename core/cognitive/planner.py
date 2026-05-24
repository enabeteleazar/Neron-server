from __future__ import annotations

from typing import Any


class Planner:
    """
    Planner minimal pour la stack cognitive de Néron.

    Rôle :
    - recevoir un objectif
    - produire un plan simple
    - rester compatible avec l'ancienne méthode plan()
    """

    def __init__(self) -> None:
        pass

    def generate_plan(
        self,
        goal: str | None,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:

        runtime_policy = (context or {}).get("runtime_policy", {}) or {}
        runtime_mode = runtime_policy.get("runtime_mode", "normal")
        heavy_reasoning_allowed = runtime_policy.get("heavy_reasoning_allowed", True)

        if not goal:
            return []

        if runtime_mode == "survival":
            return [
                {
                    "title": "Préserver le noyau Néron",
                    "description": "Limiter les actions autonomes et maintenir uniquement les services critiques.",
                    "priority": "critical",
                    "source": "planner",
                    "runtime_mode": runtime_mode,
                }
            ]

        normalized_goal = goal.lower()

        tasks: list[dict[str, Any]] = []

        if "stabilité" in normalized_goal or "stabilite" in normalized_goal:
            tasks.extend(
                [
                    {
                        "title": "Surveiller neron-core",
                        "description": "Vérifier que le service principal reste actif.",
                        "priority": "high",
                        "source": "planner",
                    },
                    {
                        "title": "Analyser les ressources système",
                        "description": "Contrôler CPU, RAM et disque via SelfModel.",
                        "priority": "high",
                        "source": "planner",
                    },
                    {
                        "title": "Contrôler la boucle cognitive",
                        "description": "Vérifier que la boucle cognitive reste active.",
                        "priority": "medium",
                        "source": "planner",
                    },
                ]
            )

        if runtime_mode in {"prudent", "degraded"}:
            light_tasks = [
                task for task in tasks
                if task.get("priority") in {"critical", "high"}
            ]

            for task in light_tasks:
                task["runtime_mode"] = runtime_mode
                task["heavy_reasoning_allowed"] = heavy_reasoning_allowed

            return light_tasks[:2]

        for task in tasks:
            task["runtime_mode"] = runtime_mode
            task["heavy_reasoning_allowed"] = heavy_reasoning_allowed

        return tasks

    def plan(
        self,
        goal: str | None,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return self.generate_plan(goal, context)


_planner: Planner | None = None


def get_planner() -> Planner:
    global _planner

    if _planner is None:
        _planner = Planner()

    return _planner
