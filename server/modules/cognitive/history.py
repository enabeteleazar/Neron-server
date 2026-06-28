from __future__ import annotations

import json
import os
import fcntl
from collections import deque
from pathlib import Path
from typing import Any


DEFAULT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 3


def append_jsonl(
    path: Path,
    payload: dict[str, Any],
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, default=str) + "\n"
    encoded_size = len(encoded.encode("utf-8"))
    lock_path = path.with_name(f".{path.name}.lock")
    with lock_path.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if path.exists() and path.stat().st_size + encoded_size > max_bytes:
            rotate_jsonl(path, backup_count=backup_count)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(encoded)


def rotate_jsonl(path: Path, *, backup_count: int = DEFAULT_BACKUP_COUNT) -> None:
    if backup_count < 1 or not path.exists():
        return
    oldest = path.with_name(f"{path.name}.{backup_count}")
    oldest.unlink(missing_ok=True)
    for index in range(backup_count - 1, 0, -1):
        source = path.with_name(f"{path.name}.{index}")
        if source.exists():
            os.replace(source, path.with_name(f"{path.name}.{index + 1}"))
    os.replace(path, path.with_name(f"{path.name}.1"))


def read_jsonl_tail(path: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists() or limit <= 0:
        return []
    lines: deque[str] = deque(maxlen=min(limit, 500))
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            lines.append(line)
    items: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            items.append(value)
    return items


def compact_cognitive_state(state: dict[str, Any]) -> dict[str, Any]:
    compact = dict(state)
    tasks = compact.get("active_tasks")
    if isinstance(tasks, list):
        compact["active_task_count"] = len(tasks)
        compact["active_tasks"] = [
            {
                key: task.get(key)
                for key in ("id", "title", "priority", "status", "source")
                if task.get(key) is not None
            }
            for task in tasks[:10]
            if isinstance(task, dict)
        ]
    return compact
