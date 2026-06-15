from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from modules.code_awareness.security import (
    CodeAwarenessSecurityError,
    relative_to_project,
    resolve_user_path,
)


MAX_BYTES = 96 * 1024
MAX_LINES = 400
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|password|passwd|secret|token|credential)\b\s*[:=]\s*['\"][^'\"]{6,}"
)


class CodeReader:
    def __init__(self, max_bytes: int = MAX_BYTES, max_lines: int = MAX_LINES) -> None:
        self.max_bytes = max_bytes
        self.max_lines = max_lines

    def read(
        self,
        path: str,
        *,
        start_line: int = 1,
        max_lines: int | None = None,
    ) -> dict[str, Any]:
        target = resolve_user_path(path)

        if not target.exists():
            raise FileNotFoundError(f"Fichier introuvable: {path}")

        if not target.is_file():
            raise IsADirectoryError(f"Chemin non fichier: {path}")

        line_limit = max(1, min(max_lines or self.max_lines, self.max_lines))
        start = max(1, start_line)
        size = target.stat().st_size

        with target.open("rb") as handle:
            chunk = handle.read(self.max_bytes + 1)

        if b"\x00" in chunk:
            raise CodeAwarenessSecurityError("Fichier binaire refusé.")

        truncated_by_size = len(chunk) > self.max_bytes or size > self.max_bytes
        text = chunk[: self.max_bytes].decode("utf-8", errors="replace")

        if self._looks_like_secret_config(target, text):
            raise CodeAwarenessSecurityError("Configuration contenant des secrets refusée.")

        all_lines = text.splitlines()
        total_lines = self._count_lines(target) if not truncated_by_size else len(all_lines)
        selected = all_lines[start - 1 : start - 1 + line_limit]
        end_line = start + len(selected) - 1 if selected else start
        truncated_by_lines = start - 1 + line_limit < len(all_lines)

        return {
            "path": relative_to_project(target),
            "lines": total_lines,
            "start_line": start,
            "end_line": end_line,
            "truncated": bool(truncated_by_size or truncated_by_lines),
            "content": "\n".join(selected),
        }

    def _count_lines(self, path: Path) -> int:
        count = 0
        with path.open("rb") as handle:
            for count, _line in enumerate(handle, start=1):
                pass
        return count

    def _looks_like_secret_config(self, path: Path, text: str) -> bool:
        name = path.name.lower()
        config_names = {
            "config.json",
            "config.yaml",
            "config.yml",
            "settings.json",
            "settings.yaml",
            "settings.yml",
        }

        return name in config_names and bool(SECRET_ASSIGNMENT_RE.search(text))


def read_file(path: str, start_line: int = 1, max_lines: int | None = None) -> dict[str, Any]:
    return CodeReader().read(path, start_line=start_line, max_lines=max_lines)
