from __future__ import annotations

from typing import Any

from modules.code_awareness.scanner import CodeScanner
from modules.code_awareness.security import relative_to_project


MAX_FILE_BYTES = 512 * 1024


class CodeSearcher:
    def __init__(self, scanner: CodeScanner | None = None) -> None:
        self.scanner = scanner or CodeScanner()

    def search(
        self,
        query: str,
        *,
        max_results: int = 50,
        case_sensitive: bool = False,
    ) -> dict[str, Any]:
        needle = (query or "").strip()
        if not needle:
            return {"query": query, "count": 0, "results": []}

        results: list[dict[str, Any]] = []
        wanted = needle if case_sensitive else needle.lower()

        for path in self.scanner.iter_files():
            if path.stat().st_size > MAX_FILE_BYTES:
                continue

            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue

            for line_number, line in enumerate(lines, start=1):
                haystack = line if case_sensitive else line.lower()
                if wanted not in haystack:
                    continue

                results.append(
                    {
                        "file": relative_to_project(path),
                        "line": line_number,
                        "excerpt": line.strip()[:220],
                    }
                )

                if len(results) >= max_results:
                    return {"query": needle, "count": len(results), "results": results}

        return {"query": needle, "count": len(results), "results": results}


def search_code(query: str, max_results: int = 50) -> dict[str, Any]:
    return CodeSearcher().search(query, max_results=max(1, min(max_results, 100)))
