import json
from pathlib import Path


EVENT_LOG_PATH = Path("/etc/neron/data/events.jsonl")


def read_events(limit: int = 20, event_type: str | None = None):
    if not EVENT_LOG_PATH.exists():
        return []

    lines = EVENT_LOG_PATH.read_text(encoding="utf-8").splitlines()

    events = []
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event_type and event.get("event_type") != event_type:
            continue

        events.append(event)

        if len(events) >= limit:
            break

    return events
