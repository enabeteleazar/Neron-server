from __future__ import annotations

import inspect
import re
import threading
from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any

from core.tools.models import ToolResult
from core.tools.registry import ToolRegistry, get_tool_registry


ToolHandler = Callable[[dict[str, Any]], ToolResult | dict[str, Any] | Awaitable[Any]]
_ERROR_PATTERN = re.compile(
    r"\b(ERROR|CRITICAL|FATAL|Traceback|Exception)\b",
    re.IGNORECASE,
)
_COMPONENT_PATTERNS = (
    re.compile(r"\b(?:component|service|module)[=: ]+([A-Za-z0-9_.-]+)", re.IGNORECASE),
    re.compile(r"\[([A-Za-z0-9_.-]+)\]"),
    re.compile(
        r"^\s*(?:ERROR|CRITICAL|FATAL|Traceback|Exception)"
        r"(?:\s*[:|-]\s*|\s+)([A-Za-z][A-Za-z0-9_.-]*)\b",
        re.IGNORECASE,
    ),
)


class ToolRuntime:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        handlers: dict[str, ToolHandler] | None = None,
        log_provider: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self.registry = registry or get_tool_registry()
        self.log_provider = log_provider
        self.handlers: dict[str, ToolHandler] = {
            "neron_log_reader_tool": self._read_logs,
            "neron_log_error_filter_tool": self._filter_errors,
            "neron_log_summary_tool": self._summarize_errors,
            **(handlers or {}),
        }

    def register_handler(self, slug: str, handler: ToolHandler) -> None:
        self.handlers[slug] = handler

    async def execute_tool(
        self,
        slug: str,
        payload: dict[str, Any] | None = None,
    ) -> ToolResult:
        spec = self.registry.get_tool(slug)
        if spec is None:
            return ToolResult(ok=False, error="tool_not_found")
        if spec.safety.get("allow_system_commands"):
            return ToolResult(ok=False, error="unsafe_tool_rejected")
        handler = self.handlers.get(slug)
        if handler is None:
            return ToolResult(ok=False, error="tool_handler_not_available")
        try:
            value = handler(dict(payload or {}))
            if inspect.isawaitable(value):
                value = await value
            return self._coerce_result(value)
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))

    def _read_logs(self, payload: dict[str, Any]) -> ToolResult:
        logs = payload.get("logs")
        if logs is None and self.log_provider is not None:
            logs = self.log_provider(payload)
        if logs is None:
            logs = []
        if isinstance(logs, str):
            lines = logs.splitlines()
        else:
            lines = [str(line) for line in logs]
        limit = max(1, min(int(payload.get("limit", 500)), 2000))
        selected = lines[-limit:]
        return ToolResult(
            ok=True,
            response=f"{len(selected)} lignes de log disponibles.",
            data={"logs": selected, "line_count": len(selected)},
        )

    def _filter_errors(self, payload: dict[str, Any]) -> ToolResult:
        logs = payload.get("logs") or []
        if isinstance(logs, str):
            logs = logs.splitlines()
        errors = [str(line) for line in logs if _ERROR_PATTERN.search(str(line))]
        return ToolResult(
            ok=True,
            response=f"{len(errors)} erreurs extraites des logs.",
            data={"errors": errors, "error_count": len(errors)},
        )

    def _summarize_errors(self, payload: dict[str, Any]) -> ToolResult:
        effective_payload = payload
        nested_payload = payload.get("payload")
        if isinstance(nested_payload, dict):
            effective_payload = {**nested_payload, **payload}
        errors = effective_payload.get("errors") or []
        if isinstance(errors, str):
            errors = errors.splitlines()
        lines = [str(line).strip() for line in errors if str(line).strip()]
        if not lines:
            return ToolResult(
                ok=True,
                response="Analyse des logs Néron : aucune erreur critique détectée.",
                data={
                    "error_count": 0,
                    "components": [],
                    "severity": "none",
                    "excerpt": "",
                    "recommendation": "Aucune action immédiate.",
                },
            )

        severity_counts = Counter(
            match.group(1).upper()
            for line in lines
            for match in [_ERROR_PATTERN.search(line)]
            if match
        )
        severity = next(
            (level for level in ("FATAL", "CRITICAL", "EXCEPTION", "TRACEBACK", "ERROR")
             if severity_counts[level]),
            "ERROR",
        ).lower()
        components = sorted(
            {
                match.group(1)
                for line in lines
                for pattern in _COMPONENT_PATTERNS
                for match in [pattern.search(line)]
                if match
            }
        )
        excerpt = lines[0][:180]
        component_text = ", ".join(components[:5]) if components else "non identifié"
        response = (
            f"Analyse des logs Néron : {len(lines)} erreur(s), gravité {severity}. "
            f"Composants : {component_text}. Extrait : {excerpt}. "
            "Recommandation : vérifier le composant concerné et corréler les événements voisins."
        )
        return ToolResult(
            ok=True,
            response=response,
            data={
                "error_count": len(lines),
                "components": components,
                "severity": severity,
                "excerpt": excerpt,
                "recommendation": (
                    "Vérifier le composant concerné et corréler les événements voisins."
                ),
            },
        )

    def _coerce_result(self, value: Any) -> ToolResult:
        if isinstance(value, ToolResult):
            return value
        if isinstance(value, dict):
            if "ok" in value:
                return ToolResult(
                    ok=bool(value.get("ok")),
                    response=str(value.get("response") or ""),
                    data=dict(value.get("data") or {}),
                    error=str(value["error"]) if value.get("error") else None,
                )
            return ToolResult(ok=True, data=value)
        return ToolResult(ok=True, response=str(value or ""))


_RUNTIME: ToolRuntime | None = None
_RUNTIME_LOCK = threading.Lock()


def get_tool_runtime() -> ToolRuntime:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            _RUNTIME = ToolRuntime()
        return _RUNTIME
