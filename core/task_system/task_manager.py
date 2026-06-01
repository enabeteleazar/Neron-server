from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASKS_FILE = Path("/etc/neron/data/tasks.json")


def normalize_task_title(title: str | None) -> str:
    if not title:
        return ""

    value = title.lower().strip()

    replacements = {
        "analyser": "surveiller",
        "contrôler": "vérifier",
        "controler": "vérifier",
        "etat": "état",
        "ressources systeme": "ressources système",
        "boucle cognitive": "boucle cognitive",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return value


class TaskManager:
    def __init__(self) -> None:
        self.tasks: list[dict[str, Any]] = []
        self._load()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load(self) -> None:
        if not TASKS_FILE.exists():
            return

        try:
            data = json.loads(TASKS_FILE.read_text())
            self.tasks = data.get("tasks", [])
        except Exception:
            self.tasks = []

    def save(self) -> None:
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.write_text(
            json.dumps(
                {"tasks": self.tasks},
                indent=2,
                ensure_ascii=False,
            )
        )

    def create_task(
        self,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        status: str = "active",
        source: str = "manual",
    ) -> dict[str, Any]:
        task = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "priority": priority,
            "status": status,
            "source": source,
            "progress": 0,
            "created_at": self._now(),
            "updated_at": self._now(),
            "completed_at": None,
        }

        self.tasks.append(task)
        self.save()
        return task

    def list_tasks(self) -> list[dict[str, Any]]:
        return self.tasks

    def list_active_tasks(self) -> list[dict[str, Any]]:
        return [
            task
            for task in self.tasks
            if task.get("status") in {"pending", "active", "todo", "in_progress"}
        ]

    def get_active_tasks(self) -> list[dict[str, Any]]:
        return self.list_active_tasks()

    def ensure_default_tasks_for_goal(self, goal: str | None) -> None:
        if not goal:
            return

        if self.list_active_tasks():
            return

        normalized_goal = goal.lower()

        if "stabilité" in normalized_goal or "stabilite" in normalized_goal:
            self.create_task(
                title="Surveiller neron-core",
                description="Vérifier que le service principal reste actif.",
                priority="high",
                source="goal_system",
            )

            self.create_task(
                title="Surveiller les ressources système",
                description="Observer CPU, RAM et disque via SelfModel.",
                priority="high",
                source="goal_system",
            )

            self.create_task(
                title="Vérifier la boucle cognitive",
                description="Confirmer que la boucle cognitive reste active.",
                priority="medium",
                source="goal_system",
            )


    def create_tasks_from_plan(
        self,
        plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        goal = str(plan.get("goal") or "")
        plan_id = str(plan.get("id") or "")
        created: list[dict[str, Any]] = []

        existing_keys = {
            (
                normalize_task_title(task.get("title")),
                task.get("source"),
                task.get("plan_id"),
            )
            for task in self.tasks
        }

        for step in plan.get("steps", []):
            title = str(step.get("title") or "").strip()
            if not title:
                continue

            key = (
                normalize_task_title(title),
                "planner",
                plan_id,
            )

            if key in existing_keys:
                continue

            task = self.create_task(
                title=title,
                description=str(step.get("description") or goal),
                priority="medium",
                status="active",
                source="planner",
            )

            task["plan_id"] = plan_id
            task["goal"] = goal
            task["agent"] = step.get("agent")
            task["action"] = step.get("action")
            task["updated_at"] = self._now()

            created.append(task)
            existing_keys.add(key)

        if created:
            self.save()

        return created


    def get_task(self, task_id: str) -> dict[str, Any] | None:
        for task in self.tasks:
            if task.get("id") == task_id:
                return task
        return None

    def next_active_task(self) -> dict[str, Any] | None:
        active_statuses = {"pending", "active", "todo", "in_progress"}

        for task in self.tasks:
            if (
                task.get("status") in active_statuses
                and task.get("source") == "planner"
                and task.get("action")
            ):
                return task

        for task in self.tasks:
            if (
                task.get("status") in active_statuses
                and task.get("action")
            ):
                return task

        for task in self.tasks:
            if task.get("status") in active_statuses:
                return task

        return None

    def update_task(
        self,
        task_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        task = self.get_task(task_id)

        if not task:
            return None

        task.update(updates)
        task["updated_at"] = self._now()
        self.save()
        return task

    def fail_task(
        self,
        task_id: str,
        error: str,
    ) -> dict[str, Any] | None:
        return self.update_task(
            task_id,
            {
                "status": "failed",
                "error": error,
                "progress": task.get("progress", 0) if (task := self.get_task(task_id)) else 0,
            },
        )

    def complete_task(self, task_id: str) -> bool:
        for task in self.tasks:
            if task.get("id") == task_id:
                task["status"] = "completed"
                task["progress"] = 100
                task["updated_at"] = self._now()
                task["completed_at"] = self._now()
                self.save()
                return True

        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tasks": self.tasks,
            "active_tasks": self.list_active_tasks(),
        }


_task_manager: TaskManager | None = None


def get_task_manager() -> TaskManager:
    global _task_manager

    if _task_manager is None:
        _task_manager = TaskManager()

    return _task_manager
