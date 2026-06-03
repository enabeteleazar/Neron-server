from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal
import json
from pathlib import Path


TaskStatus = Literal["created", "planned", "waiting_validation", "done", "failed"]


@dataclass
class AutonomousTask:
    objective: str
    plan: list[str]
    status: TaskStatus
    created_at: str
    updated_at: str
    verification: str | None = None
    memory_path: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class TaskStore:
    def __init__(self, path: str = "/etc/neron/data/autonomous_tasks.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save_all(self, tasks: list[dict]) -> None:
        self.path.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def add(self, task: AutonomousTask) -> dict:
        tasks = self.load()
        data = task.to_dict()
        tasks.append(data)
        self.save_all(tasks)
        return data
