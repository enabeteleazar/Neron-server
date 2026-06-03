from __future__ import annotations

import json
from pathlib import Path
from typing import Any


GOALS_FILE = Path("/etc/neron/data/goals.json")


class GoalSystem:
    def __init__(self) -> None:
        self.active_goal: str | None = None
        self.goals_history: list[str] = []
        self.long_term_goals: list[str] = []
        self._load()

    def _load(self) -> None:
        if not GOALS_FILE.exists():
            return

        try:
            data = json.loads(GOALS_FILE.read_text())
            self.active_goal = data.get("active_goal")
            self.goals_history = data.get("goals_history", [])
            self.long_term_goals = data.get("long_term_goals", [])
        except Exception:
            pass

    def save(self) -> None:
        GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "active_goal": self.active_goal,
            "goals_history": self.goals_history,
            "long_term_goals": self.long_term_goals,
        }

        GOALS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def set_active_goal(self, goal: str) -> None:
        self.active_goal = goal

        if goal not in self.goals_history:
            self.goals_history.append(goal)

        self.save()

    def get_active_goal(self) -> str | None:
        return self.active_goal

    def add_long_term_goal(self, goal: str) -> None:
        if goal not in self.long_term_goals:
            self.long_term_goals.append(goal)

        self.save()

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_goal": self.active_goal,
            "goals_history": self.goals_history,
            "long_term_goals": self.long_term_goals,
        }


_goal_system: GoalSystem | None = None


def get_goal_system() -> GoalSystem:
    global _goal_system

    if _goal_system is None:
        _goal_system = GoalSystem()

    return _goal_system
