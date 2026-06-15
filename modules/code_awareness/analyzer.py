from __future__ import annotations

import ast
from typing import Any

from modules.code_awareness.reader import CodeReader


HTTP_DECORATORS = {"get", "post", "put", "patch", "delete", "websocket"}


class CodeAnalyzer:
    def __init__(self, reader: CodeReader | None = None) -> None:
        self.reader = reader or CodeReader(max_bytes=512 * 1024, max_lines=5000)

    def analyze(self, path: str) -> dict[str, Any]:
        payload = self.reader.read(path, max_lines=5000)
        source = payload["content"]

        try:
            tree = ast.parse(source, filename=payload["path"])
        except SyntaxError as exc:
            return {
                "path": payload["path"],
                "syntax_error": {
                    "line": exc.lineno,
                    "message": exc.msg,
                },
                "imports": [],
                "classes": [],
                "functions": [],
                "routes": [],
                "dependencies": [],
                "responsibility": "Fichier Python non analysable par AST.",
            }

        imports = self._imports(tree)
        classes = self._classes(tree)
        functions = self._functions(tree)
        routes = self._routes(tree)
        dependencies = self._dependencies(imports)

        return {
            "path": payload["path"],
            "lines": payload["lines"],
            "imports": imports,
            "classes": classes,
            "functions": functions,
            "routes": routes,
            "decorators": sorted({decorator for route in routes for decorator in route["decorators"]}),
            "dependencies": dependencies,
            "responsibility": self._responsibility(payload["path"], classes, functions, routes),
        }

    def _imports(self, tree: ast.AST) -> list[dict[str, Any]]:
        imports: list[dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        {
                            "module": alias.name,
                            "name": alias.asname or alias.name,
                            "line": node.lineno,
                            "type": "import",
                        }
                    )
            elif isinstance(node, ast.ImportFrom):
                module = "." * node.level + (node.module or "")
                for alias in node.names:
                    imports.append(
                        {
                            "module": module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                            "type": "from",
                        }
                    )

        return imports

    def _classes(self, tree: ast.AST) -> list[dict[str, Any]]:
        classes: list[dict[str, Any]] = []

        for node in tree.body if isinstance(tree, ast.Module) else []:
            if not isinstance(node, ast.ClassDef):
                continue

            classes.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "methods": [
                        item.name
                        for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    ],
                    "decorators": [self._decorator_name(item) for item in node.decorator_list],
                }
            )

        return classes

    def _functions(self, tree: ast.AST) -> list[dict[str, Any]]:
        functions: list[dict[str, Any]] = []

        for node in tree.body if isinstance(tree, ast.Module) else []:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            functions.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "async": isinstance(node, ast.AsyncFunctionDef),
                    "decorators": [self._decorator_name(item) for item in node.decorator_list],
                }
            )

        return functions

    def _routes(self, tree: ast.AST) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            decorators = [self._decorator_name(item) for item in node.decorator_list]
            http_decorators = [
                decorator
                for decorator in decorators
                if decorator.split(".")[-1] in HTTP_DECORATORS
            ]

            if not http_decorators:
                continue

            routes.append(
                {
                    "function": node.name,
                    "line": node.lineno,
                    "path": self._route_path(node.decorator_list),
                    "decorators": http_decorators,
                }
            )

        return routes

    def _decorator_name(self, decorator: ast.AST) -> str:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator

        if isinstance(target, ast.Attribute):
            prefix = self._decorator_name(target.value)
            return f"{prefix}.{target.attr}" if prefix else target.attr

        if isinstance(target, ast.Name):
            return target.id

        return ""

    def _route_path(self, decorators: list[ast.expr]) -> str | None:
        for decorator in decorators:
            if not isinstance(decorator, ast.Call):
                continue

            name = self._decorator_name(decorator)
            if name.split(".")[-1] not in HTTP_DECORATORS:
                continue

            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                return str(decorator.args[0].value)

        return None

    def _dependencies(self, imports: list[dict[str, Any]]) -> list[str]:
        dependencies: set[str] = set()

        for item in imports:
            module = str(item.get("module") or "").lstrip(".")
            if module.startswith("core."):
                parts = module.split(".")
                dependencies.add(".".join(parts[:3]) if len(parts) >= 3 else module)
            elif module.startswith("agents."):
                parts = module.split(".")
                dependencies.add(".".join(parts[:2]) if len(parts) >= 2 else module)

        return sorted(dependencies)

    def _responsibility(
        self,
        path: str,
        classes: list[dict[str, Any]],
        functions: list[dict[str, Any]],
        routes: list[dict[str, Any]],
    ) -> str:
        lowered = path.lower()

        if routes:
            return "Exposition d'API FastAPI."
        if "goal" in lowered and "orchestrator" in lowered:
            return "Orchestration Goal -> Plan -> Critic -> Execution."
        if "planning" in lowered and "executor" in lowered:
            return "Execution des etapes de planification."
        if "planning" in lowered and "planner" in lowered:
            return "Generation de plans et de taches."
        if "telegram" in lowered:
            return "Interface de communication Telegram."
        if "task_system" in lowered:
            return "Gestion ou execution des taches."
        if classes:
            return f"Definition de classe principale: {classes[0]['name']}."
        if functions:
            return "Fonctions utilitaires ou logique de module."
        return "Responsabilite non deduite automatiquement."


def analyze_file(path: str) -> dict[str, Any]:
    return CodeAnalyzer().analyze(path)
