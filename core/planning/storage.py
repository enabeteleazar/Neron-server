from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_PLAN_HISTORY_PATH = Path("/etc/neron/data/plans.jsonl")


class PlanStorage:
    def __init__(self, path: Path = DEFAULT_PLAN_HISTORY_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, plan: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(plan, ensure_ascii=False) + "\n")

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        plans = self._read_all()
        return list(reversed(plans[-limit:]))

    def last(self) -> dict[str, Any] | None:
        plans = self._read_all()
        return plans[-1] if plans else None

    def get(self, plan_id: str) -> dict[str, Any] | None:
        for plan in reversed(self._read_all()):
            if plan.get("id") == plan_id:
                return plan
        return None

    def update(self, updated_plan: dict[str, Any]) -> None:
        plans = self._read_all()
        plan_id = updated_plan.get("id")
        written = False

        with self.path.open("w", encoding="utf-8") as f:
            for plan in plans:
                if plan.get("id") == plan_id:
                    f.write(json.dumps(updated_plan, ensure_ascii=False) + "\n")
                    written = True
                else:
                    f.write(json.dumps(plan, ensure_ascii=False) + "\n")

            if not written:
                f.write(json.dumps(updated_plan, ensure_ascii=False) + "\n")

    def _read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        plans = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                plans.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return plans
