from __future__ import annotations

import re
import threading
import unicodedata
from typing import Any

from core.tools.models import ToolResult, ToolSpec
from core.tools.registry import ToolRegistry, get_tool_registry
from core.tools.runtime import ToolRuntime, get_tool_runtime


LOG_TOOL_SLUGS = (
    "neron_log_reader_tool",
    "neron_log_error_filter_tool",
    "neron_log_summary_tool",
)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return " ".join(normalized.split())


class ToolCreator:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        runtime: ToolRuntime | None = None,
    ) -> None:
        self.registry = registry or get_tool_registry()
        self.runtime = runtime or (
            ToolRuntime(self.registry) if registry is not None else get_tool_runtime()
        )

    def plan_tools_for_request(self, text: str) -> list[ToolSpec]:
        query = _normalize(text)
        if "log" not in query and "journal" not in query:
            return []
        return self._log_tool_specs()

    def create_tool(self, spec: ToolSpec) -> ToolSpec:
        errors = self.validate_tool(spec)
        if errors:
            raise ValueError("; ".join(errors))
        return self.register_tool(spec)

    def validate_tool(self, spec: ToolSpec) -> list[str]:
        errors: list[str] = []
        if not spec.name.strip():
            errors.append("tool_name_required")
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", spec.slug):
            errors.append("invalid_tool_slug")
        if not spec.description.strip():
            errors.append("tool_description_required")
        if spec.safety.get("allow_system_commands"):
            errors.append("system_commands_not_allowed")
        return errors

    def register_tool(self, spec: ToolSpec) -> ToolSpec:
        return self.registry.register_tool(spec)

    def ensure_tools_for_request(self, text: str) -> dict[str, Any]:
        planned = self.plan_tools_for_request(text)
        created: list[str] = []
        existing: list[str] = []
        for spec in planned:
            if self.registry.tool_exists(spec.slug):
                existing.append(spec.slug)
                continue
            self.create_tool(spec)
            created.append(spec.slug)
        required = [spec.slug for spec in planned]
        return {
            "status": "ready" if required else "not_planned",
            "required_tools": required,
            "created_tools": created,
            "existing_tools": existing,
            "tool_creation_status": "ready" if required else "not_required",
        }

    async def execute_tools_for_request(
        self,
        text: str,
        payload: dict[str, Any] | None = None,
    ) -> ToolResult:
        ensured = self.ensure_tools_for_request(text)
        if ensured["required_tools"] != list(LOG_TOOL_SLUGS):
            return ToolResult(ok=False, error="tool_plan_not_available")
        reader = await self.runtime.execute_tool(
            "neron_log_reader_tool",
            payload or {},
        )
        if not reader.ok:
            return reader
        filtered = await self.runtime.execute_tool(
            "neron_log_error_filter_tool",
            {"logs": reader.data.get("logs", [])},
        )
        if not filtered.ok:
            return filtered
        return await self.runtime.execute_tool(
            "neron_log_summary_tool",
            {"errors": filtered.data.get("errors", [])},
        )

    def _log_tool_specs(self) -> list[ToolSpec]:
        common_safety = {
            "level": "low",
            "allow_system_commands": False,
            "network_access": False,
            "filesystem_access": False,
        }
        return [
            ToolSpec(
                name="Lecteur de logs Néron",
                slug="neron_log_reader_tool",
                description=(
                    "Collecte des lignes de logs fournies par un payload ou un provider injecté."
                ),
                inputs={"logs": "string|list[string]", "limit": "integer"},
                outputs={"logs": "list[string]", "line_count": "integer"},
                safety=dict(common_safety),
                metadata={"aliases": ["lire les logs Néron", "logs Néron"]},
            ),
            ToolSpec(
                name="Filtre d'erreurs des logs Néron",
                slug="neron_log_error_filter_tool",
                description=(
                    "Extrait les lignes ERROR, CRITICAL, FATAL, Traceback et Exception."
                ),
                inputs={"logs": "list[string]"},
                outputs={"errors": "list[string]", "error_count": "integer"},
                safety=dict(common_safety),
                metadata={"aliases": ["filtrer les erreurs des logs"]},
            ),
            ToolSpec(
                name="Résumé des erreurs des logs Néron",
                slug="neron_log_summary_tool",
                description=(
                    "Résume le nombre d'erreurs, les composants, la gravité et une recommandation."
                ),
                inputs={"errors": "list[string]"},
                outputs={
                    "error_count": "integer",
                    "components": "list[string]",
                    "severity": "string",
                    "excerpt": "string",
                    "recommendation": "string",
                },
                safety=dict(common_safety),
                metadata={"aliases": ["résumer les erreurs critiques"]},
            ),
        ]


_CREATOR: ToolCreator | None = None
_CREATOR_LOCK = threading.Lock()


def get_tool_creator() -> ToolCreator:
    global _CREATOR
    with _CREATOR_LOCK:
        if _CREATOR is None:
            _CREATOR = ToolCreator()
        return _CREATOR
