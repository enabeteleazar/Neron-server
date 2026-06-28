from __future__ import annotations

from pathlib import Path
from typing import Any

from modules.code_awareness.security import (
    ALLOWED_TOP_LEVEL_DIRS,
    DENIED_DIR_NAMES,
    is_allowed_scan_path,
    project_root,
    relative_to_project,
)


class CodeScanner:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or project_root()).resolve()

    def scan(self, max_depth: int = 3) -> dict[str, Any]:
        files = self.iter_files()
        python_files = [path for path in files if path.suffix == ".py"]
        packages = self._packages(python_files)

        return {
            "root": str(self.root),
            "allowed_dirs": sorted(ALLOWED_TOP_LEVEL_DIRS),
            "ignored_dirs": sorted(DENIED_DIR_NAMES),
            "files": len(files),
            "modules": len(python_files),
            "packages": packages[:80],
            "tree": self.tree(max_depth=max_depth),
        }

    def iter_files(self) -> list[Path]:
        files: list[Path] = []

        for dirname in sorted(ALLOWED_TOP_LEVEL_DIRS):
            base = self.root / dirname
            if not base.exists():
                continue

            for path in base.rglob("*"):
                if not is_allowed_scan_path(path):
                    continue

                if path.is_file():
                    files.append(path)

        return sorted(files)

    def tree(self, max_depth: int = 3) -> dict[str, Any]:
        nodes = []

        for dirname in sorted(ALLOWED_TOP_LEVEL_DIRS):
            base = self.root / dirname
            if not base.exists() or not is_allowed_scan_path(base):
                continue

            nodes.append(self._tree_node(base, depth=0, max_depth=max_depth))

        return {
            "name": self.root.name,
            "path": ".",
            "type": "directory",
            "children": nodes,
        }

    def _tree_node(self, path: Path, depth: int, max_depth: int) -> dict[str, Any]:
        node_type = "directory" if path.is_dir() else "file"
        node = {
            "name": path.name,
            "path": relative_to_project(path),
            "type": node_type,
        }

        if path.is_file() or depth >= max_depth:
            return node

        children = []
        for child in sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name)):
            if not is_allowed_scan_path(child):
                continue
            children.append(self._tree_node(child, depth + 1, max_depth))

        node["children"] = children
        return node

    def _packages(self, python_files: list[Path]) -> list[str]:
        packages: set[str] = set()

        for path in python_files:
            relative = path.relative_to(self.root)
            if len(relative.parts) <= 1:
                continue

            if path.name == "__init__.py":
                packages.add(".".join(relative.parent.parts))
            else:
                packages.add(".".join(relative.parent.parts))

        return sorted(packages)


def scan_project(max_depth: int = 3) -> dict[str, Any]:
    return CodeScanner().scan(max_depth=max_depth)
