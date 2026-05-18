from __future__ import annotations

import json
from pathlib import Path

from core.task_system.task_model import Task


class TaskStore:
    def __init__(self, path: str = "/etc/neron/data/tasks.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self.save_all([])

    def load_all(self) -> list[Task]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))

            if not isinstance(raw, list):
                return []

            return [Task.from_dict(item) for item in raw if isinstance(item, dict)]

        except Exception:
            return []

    def save_all(self, tasks: list[Task]) -> None:
        data = [task.to_dict() for task in tasks]

        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
