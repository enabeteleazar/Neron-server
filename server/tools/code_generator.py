from __future__ import annotations

import ast
import re
from abc import ABC, abstractmethod
from pathlib import Path

from modules.evolution.codex_runner import CodexRunner
from tools.models import ToolNeed, ToolSpec
from tools.templates import (
    codex_prompt,
    deterministic_tool_code,
    deterministic_tool_test,
)


FORBIDDEN_IMPORTS = {
    "os",
    "pathlib",
    "requests",
    "shutil",
    "socket",
    "subprocess",
    "urllib",
}
FORBIDDEN_CALLS = {
    "__import__",
    "compile",
    "eval",
    "exec",
    "open",
}


class ToolCodeGenerator(ABC):
    @abstractmethod
    def can_generate(self, need: ToolNeed) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def generate_tool_code(self, spec: ToolSpec, need: ToolNeed) -> str:
        raise NotImplementedError

    @abstractmethod
    async def generate_tests(self, spec: ToolSpec, need: ToolNeed) -> str:
        raise NotImplementedError


class DeterministicToolCodeGenerator(ToolCodeGenerator):
    SUPPORTED_INTENTS = {
        "analyze",
        "summarize",
        "count",
        "compare",
        "diagnose",
        "monitor",
        "notify",
        "calculate",
        "search",
        "execute",
    }

    def can_generate(self, need: ToolNeed) -> bool:
        return need.intent in self.SUPPORTED_INTENTS

    async def generate_tool_code(self, spec: ToolSpec, need: ToolNeed) -> str:
        return deterministic_tool_code(spec, need)

    async def generate_tests(self, spec: ToolSpec, need: ToolNeed) -> str:
        path = str(need.metadata.get("tool_path") or f"{spec.slug}.py")
        return deterministic_tool_test(spec, path)


class CodexToolCodeGenerator(ToolCodeGenerator):
    def __init__(
        self,
        *,
        workspace: Path = Path("/etc/neron/workspace/tools"),
        runner: CodexRunner | None = None,
    ) -> None:
        self.workspace = workspace
        self.runner = runner or CodexRunner(workspace=workspace)

    def can_generate(self, need: ToolNeed) -> bool:
        return True

    async def generate_tool_code(self, spec: ToolSpec, need: ToolNeed) -> str:
        result = await self.runner.run_codex(
            codex_prompt(spec, need, artifact="implementation"),
            run_id=f"tool_{spec.slug}",
        )
        if not result.ok:
            raise RuntimeError(result.stderr or result.stdout or "codex_tool_generation_failed")
        return _strip_code_fence(result.stdout)

    async def generate_tests(self, spec: ToolSpec, need: ToolNeed) -> str:
        result = await self.runner.run_codex(
            codex_prompt(spec, need, artifact="unit test"),
            run_id=f"tool_test_{spec.slug}",
        )
        if not result.ok:
            raise RuntimeError(result.stderr or result.stdout or "codex_test_generation_failed")
        return _strip_code_fence(result.stdout)


def validate_generated_code(code: str) -> list[str]:
    errors: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"invalid_python:{exc.msg}"]

    has_execute = False
    has_tool_result = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in FORBIDDEN_IMPORTS:
                    errors.append(f"forbidden_import:{root}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in FORBIDDEN_IMPORTS:
                errors.append(f"forbidden_import:{root}")
            if node.module == "tools.models" and any(
                alias.name == "ToolResult" for alias in node.names
            ):
                has_tool_result = True
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "execute":
                has_execute = True
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                errors.append(f"forbidden_call:{node.func.id}")
    if not has_execute:
        errors.append("execute_function_required")
    if not has_tool_result:
        errors.append("tool_result_required")
    return sorted(set(errors))


def validate_workspace_path(path: Path, workspace: Path) -> bool:
    try:
        path.resolve().relative_to(workspace.resolve())
    except ValueError:
        return False
    return True


def _strip_code_fence(value: str) -> str:
    text = value.strip()
    match = re.fullmatch(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text
