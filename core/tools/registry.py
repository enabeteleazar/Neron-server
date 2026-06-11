from __future__ import annotations

import json
import threading
import unicodedata
from pathlib import Path

from core.tools.models import ToolSpec


DEFAULT_REGISTRY_PATH = Path("/etc/neron/data/tool_registry.json")


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return " ".join(normalized.split())


class ToolRegistry:
    def __init__(self, path: Path | None = DEFAULT_REGISTRY_PATH) -> None:
        self.path = path
        self._tools: dict[str, ToolSpec] = {}
        self._load()

    def register_tool(self, spec: ToolSpec) -> ToolSpec:
        self._tools[spec.slug] = spec
        self._save()
        return spec

    def get_tool(self, slug: str) -> ToolSpec | None:
        return self._tools.get(slug)

    def list_tools(self) -> list[ToolSpec]:
        return sorted(self._tools.values(), key=lambda spec: spec.slug)

    def find_tool_for_request(self, text: str) -> ToolSpec | None:
        query = _normalize(text)
        query_tokens = {token for token in query.split() if len(token) >= 3}
        best: tuple[float, ToolSpec] | None = None
        for spec in self._tools.values():
            aliases = list(spec.metadata.get("aliases") or [])
            haystack = _normalize(
                " ".join([spec.slug, spec.name, spec.description, *map(str, aliases)])
            )
            tokens = {token for token in haystack.split() if len(token) >= 3}
            overlap = len(query_tokens & tokens) / max(1, len(query_tokens))
            if overlap >= 0.34 and (best is None or overlap > best[0]):
                best = (overlap, spec)
        return best[1] if best else None

    def tool_exists(self, slug: str) -> bool:
        return slug in self._tools

    def _load(self) -> None:
        if self.path is None or not self.path.is_file():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        items = payload.get("tools", []) if isinstance(payload, dict) else []
        for item in items:
            if isinstance(item, dict):
                spec = ToolSpec.from_dict(item)
                if spec.slug:
                    self._tools[spec.slug] = spec

    def _save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"tools": [spec.to_dict() for spec in self.list_tools()]}
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)


_REGISTRY: ToolRegistry | None = None
_REGISTRY_LOCK = threading.Lock()


def get_tool_registry() -> ToolRegistry:
    global _REGISTRY
    with _REGISTRY_LOCK:
        if _REGISTRY is None:
            _REGISTRY = ToolRegistry()
        return _REGISTRY
