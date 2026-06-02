from __future__ import annotations

import importlib.util
import json
import unicodedata
from pathlib import Path
from typing import Any


AGENT_REGISTRY = {}


class DynamicAgentRegistry:

    def __init__(self, generated_dir: Path | str | None = None):
        self.generated_dir = Path(generated_dir or "/etc/neron/core/agents/generated")
        self._records: dict[str, dict[str, Any]] = {}

    def load_generated_agents(self):
        AGENT_REGISTRY.clear()
        self._records.clear()

        if not self.generated_dir.exists():
            return AGENT_REGISTRY

        for file in self.generated_dir.glob("*.py"):

            if file.name.startswith("_"):
                continue

            module_name = file.stem

            spec = importlib.util.spec_from_file_location(
                f"generated.{module_name}",
                file,
            )

            if not spec or not spec.loader:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "Agent"):
                agent = module.Agent()
                AGENT_REGISTRY[module_name] = agent
                record = self._build_record(module_name, file, module, agent)
                self._records[module_name] = record

        return AGENT_REGISTRY

    def find_registered_agent_for_spec(
        self,
        spec: dict[str, Any],
        spec_signature: str | None = None,
    ) -> dict[str, Any] | None:
        self.load_generated_agents()

        desired_name = self._normalize(str(spec.get("name") or ""))
        desired_signature = spec_signature or self.spec_signature(spec)

        for record in self._records.values():
            registered_signature = str(record.get("spec_signature") or "")
            if desired_signature and registered_signature and registered_signature == desired_signature:
                return record

            registered_name = self._normalize(str(record.get("agent_name") or record.get("module_name") or ""))
            has_registered_spec = bool(record.get("spec"))
            if desired_name and registered_name == desired_name and not has_registered_spec:
                return record

        return None

    def _build_record(self, module_name: str, path: Path, module: Any, agent: Any) -> dict[str, Any]:
        agent_name = str(getattr(agent, "name", module_name) or module_name)
        raw_spec = (
            getattr(module, "AGENT_SPEC", None)
            or getattr(agent, "agent_spec", None)
            or getattr(agent, "spec", None)
        )
        spec = raw_spec if isinstance(raw_spec, dict) else None
        spec_signature = (
            str(getattr(module, "AGENT_SPEC_SIGNATURE", "") or "")
            or (self.spec_signature(spec) if spec else "")
        )

        return {
            "module_name": module_name,
            "agent_name": agent_name,
            "path": str(path),
            "spec": spec,
            "spec_signature": spec_signature,
        }

    def spec_signature(self, spec: dict[str, Any] | None) -> str:
        if not spec:
            return ""
        return self._normalize_for_key(json.dumps(spec, sort_keys=True, ensure_ascii=False))

    def _normalize(self, value: str) -> str:
        text = unicodedata.normalize("NFKD", value.lower())
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        cleaned = []
        for char in text:
            cleaned.append(char if char.isalnum() else " ")
        return " ".join("".join(cleaned).split())

    def _normalize_for_key(self, value: str) -> str:
        return self._normalize(value)
