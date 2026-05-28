import json
from datetime import datetime, timezone
from pathlib import Path


EVENT_LOG_PATH = Path("/etc/neron/data/events.jsonl")


def log_event(event_type: str, payload: dict):
    EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "payload": payload,
    }

    with EVENT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
