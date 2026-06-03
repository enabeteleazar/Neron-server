from __future__ import annotations

import ast
from typing import Any

from core.code_awareness.scanner import CodeScanner
from core.code_awareness.security import relative_to_project


class DependencyMapper:
    def __init__(self, scanner: CodeScanner | None = None) -> None:
        self.scanner = scanner or CodeScanner()

    def map(self, *, max_files: int = 250) -> dict[str, Any]:
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, str]] = []
        module_by_file: dict[str, str] = {}

        python_files = [path for path in self.scanner.iter_files() if path.suffix == ".py"][:max_files]

        for path in python_files:
            file_path = relative_to_project(path)
            module = self._module_name(file_path)
            module_by_file[file_path] = module
            nodes[module] = {"module": module, "file": file_path}

        known_modules = set(nodes)

        for path in python_files:
            file_path = relative_to_project(path)
            source = module_by_file[file_path]

            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=file_path)
            except SyntaxError:
                continue

            for imported in self._imports(tree, source):
                target = self._match_known_module(imported, known_modules)
                if target and target != source:
                    edges.append({"from": source, "to": target, "type": "import"})

        return {
            "nodes": list(nodes.values()),
            "edges": self._dedupe_edges(edges),
            "summary": {
                "modules": len(nodes),
                "dependencies": len(self._dedupe_edges(edges)),
            },
        }

    def _module_name(self, file_path: str) -> str:
        if file_path.endswith("/__init__.py"):
            return file_path[: -len("/__init__.py")].replace("/", ".")
        if file_path.endswith(".py"):
            return file_path[:-3].replace("/", ".")
        return file_path.replace("/", ".")

    def _imports(self, tree: ast.AST, source_module: str) -> set[str]:
        imports: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(("core.", "agents.", "tests.", "scripts.")):
                        imports.add(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = self._resolve_from_import(node, source_module)
                if module.startswith(("core.", "agents.", "tests.", "scripts.")):
                    imports.add(module)
                    for alias in node.names:
                        if alias.name != "*":
                            imports.add(f"{module}.{alias.name}")

        return imports

    def _resolve_from_import(self, node: ast.ImportFrom, source_module: str) -> str:
        module = node.module or ""

        if node.level <= 0:
            return module

        parts = source_module.split(".")
        package_parts = parts[:-1]
        base = package_parts[: max(0, len(package_parts) - node.level + 1)]
        if module:
            base.extend(module.split("."))

        return ".".join(part for part in base if part)

    def _match_known_module(self, imported: str, known_modules: set[str]) -> str | None:
        current = imported

        while current:
            if current in known_modules:
                return current

            if "." not in current:
                break

            current = current.rsplit(".", 1)[0]

        return None

    def _dedupe_edges(self, edges: list[dict[str, str]]) -> list[dict[str, str]]:
        seen: set[tuple[str, str, str]] = set()
        unique: list[dict[str, str]] = []

        for edge in edges:
            marker = (edge["from"], edge["to"], edge["type"])
            if marker in seen:
                continue

            seen.add(marker)
            unique.append(edge)

        return unique


def map_dependencies(max_files: int = 250) -> dict[str, Any]:
    return DependencyMapper().map(max_files=max_files)
