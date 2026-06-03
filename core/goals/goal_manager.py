from __future__ import annotations

import time
from typing import Any

from core.goals.goal import Goal
from core.goals.persistence import load_goals_state, save_goals_state


PRIORITY_WEIGHT = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


class GoalManager:
    def _load_goals(self) -> list[Goal]:
        data = load_goals_state()
        return [Goal.from_dict(item) for item in data.get("goals", [])]

    def _save_goals(self, goals: list[Goal], active_goal_id: str | None = None) -> None:
        data = load_goals_state()

        if active_goal_id is None:
            active = self._select_active_goal(goals)
            active_goal_id = active.id if active else None

        data["goals"] = [goal.to_dict() for goal in goals][-50:]
        data["active_goal_id"] = active_goal_id
        data["last_update"] = time.time()

        save_goals_state(data)

    def _select_active_goal(self, goals: list[Goal]) -> Goal | None:
        candidates = [
            goal for goal in goals
            if goal.status in ("pending", "active")
        ]

        if not candidates:
            return None

        return sorted(
            candidates,
            key=lambda goal: (
                PRIORITY_WEIGHT.get(goal.priority, 2),
                goal.created_at,
            ),
            reverse=True,
        )[0]

    def list_goals(self) -> list[dict[str, Any]]:
        return [goal.to_dict() for goal in self._load_goals()]

    def get_goal(self, goal_id: str) -> dict[str, Any] | None:
        for goal in self._load_goals():
            if goal.id == goal_id:
                return goal.to_dict()
        return None

    def get_active_goal(self) -> dict[str, Any] | None:
        goals = self._load_goals()
        active = self._select_active_goal(goals)

        if not active:
            return None

        if active.status == "pending":
            active.status = "active"
            active.updated_at = time.time()
            self._save_goals(goals, active.id)

        return active.to_dict()

    def create_goal(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        source: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        goals = self._load_goals()

        for goal in goals:
            if goal.title == title and goal.status in ("pending", "active"):
                return goal.to_dict()

        goal = Goal.create(
            title=title,
            description=description,
            priority=priority,
            source=source,
            metadata=metadata,
        )

        goals.append(goal)
        self._save_goals(goals)

        return goal.to_dict()

    def update_status(self, goal_id: str, status: str) -> dict[str, Any] | None:
        goals = self._load_goals()

        for goal in goals:
            if goal.id == goal_id:
                goal.status = status
                goal.updated_at = time.time()

                if status == "completed":
                    goal.progress = 1.0

                self._save_goals(goals)
                return goal.to_dict()

        return None

    def update_progress(self, goal_id: str, progress: float) -> dict[str, Any] | None:
        goals = self._load_goals()

        for goal in goals:
            if goal.id == goal_id:
                goal.progress = max(0.0, min(1.0, progress))
                goal.updated_at = time.time()

                self._save_goals(goals)
                return goal.to_dict()

        return None

    def ensure_core_goals(self) -> None:
        self.create_goal(
            title="Maintenir la stabilité système",
            description="Surveiller l’état interne de Néron et maintenir ses services critiques opérationnels.",
            priority="high",
            source="core",
        )

        self.create_goal(
            title="Maintenir la disponibilité du LLM",
            description="Garantir que le service LLM local reste disponible pour les agents.",
            priority="high",
            source="core",
        )

        self.create_goal(
            title="Maintenir la conscience environnementale",
            description="Surveiller le réseau, Home Assistant, Ollama et les API locales via le WorldModel.",
            priority="medium",
            source="core",
        )


_GOAL_MANAGER: GoalManager | None = None


def get_goal_manager() -> GoalManager:
    global _GOAL_MANAGER

    if _GOAL_MANAGER is None:
        _GOAL_MANAGER = GoalManager()

    return _GOAL_MANAGER
