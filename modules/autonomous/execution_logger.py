from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


class ExecutionLogger:
    def __init__(self, path: str = "/etc/neron/logs/executions.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **metadata) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **metadata,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
