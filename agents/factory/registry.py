from __future__ import annotations

import importlib.util
import inspect
import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


AGENT_REGISTRY = {}
DEFAULT_GENERATED_AGENTS = Path("/etc/neron/data/generated_agents")


class DynamicAgentRegistry:

    def __init__(self, generated_dir: Path | str | None = None):
        self.generated_dir = Path(generated_dir or DEFAULT_GENERATED_AGENTS)
        self._records: dict[str, dict[str, Any]] = {}
        self._invalid_records: dict[str, dict[str, Any]] = {}

    def load_generated_agents(self):
        AGENT_REGISTRY.clear()
        self._records.clear()
        self._invalid_records.clear()

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
                self._record_invalid(file, "module_spec_unavailable")
                continue

            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as exc:
                self._record_invalid(file, f"import_failed:{exc}")
                continue

            if hasattr(module, "Agent"):
                try:
                    agent = module.Agent()
                except Exception as exc:
                    self._record_invalid(file, f"agent_init_failed:{exc}")
                    continue
                if not self._is_loadable_agent(agent):
                    self._record_invalid(file, "async_execute_contract_missing")
                    continue
                AGENT_REGISTRY[module_name] = agent
                record = self._build_record(module_name, file, module, agent)
                self._records[module_name] = record
            else:
                self._record_invalid(file, "class_agent_missing")

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
            "match_text": self._match_text(module_name, agent_name, module, agent, spec),
        }

    def list_agent_records(self) -> list[dict[str, Any]]:
        self.load_generated_agents()
        return list(self._records.values())

    def validation_index(self) -> dict[str, Any]:
        self.load_generated_agents()
        scanned_at = datetime.now(timezone.utc).isoformat()
        agents: dict[str, dict[str, Any]] = {}
        for name, record in self._records.items():
            path = Path(str(record["path"]))
            agents[name] = {
                "agent_name": str(record.get("agent_name") or name),
                "path": str(path),
                "status": "active",
                "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
                "last_scanned_at": scanned_at,
                "validation_ok": True,
                "error": None,
                "source": "dynamic_registry",
            }
        agents.update(self._invalid_records)
        return {
            "agents": dict(sorted(agents.items())),
            "last_scanned_at": scanned_at,
            "source": "dynamic_registry",
        }

    def scan(self) -> dict[str, Any]:
        index = self.validation_index()
        records = list(index["agents"].values())
        return {
            "status": "ok",
            "scanned": len(records),
            "active": sum(item.get("status") == "active" for item in records),
            "invalid": sum(item.get("status") == "invalid" for item in records),
            "runtime_reloaded": False,
            "runtime_reload": None,
            "stale_removed": [],
            "agents": records,
            "source": "dynamic_registry",
        }

    def diagnose_consistency(
        self,
        *,
        projects: Iterable[dict[str, Any]] = (),
        workspace_agents: Path | str | None = None,
    ) -> dict[str, Any]:
        self.load_generated_agents()
        generated_files = {
            path.stem: path
            for path in self._agent_files()
        }
        registered = set(self._records)
        tracked: set[str] = set()
        stale_projects: list[dict[str, str]] = []

        for project in projects:
            if not isinstance(project, dict):
                continue
            agent_name = str(project.get("registered_agent") or "").strip()
            if project.get("registry_status") != "registered" or not agent_name:
                continue
            tracked.add(agent_name)
            if agent_name not in generated_files:
                stale_projects.append(
                    {
                        "project_id": str(project.get("project_id") or ""),
                        "agent": agent_name,
                    }
                )

        workspace = Path(workspace_agents) if workspace_agents is not None else None
        workspace_only = []
        if workspace is not None and workspace.is_dir():
            workspace_only = sorted(
                path.stem
                for path in workspace.glob("*.py")
                if path.is_file() and path.stem not in generated_files
            )

        return {
            "generated_dir": str(self.generated_dir),
            "registered_agents": sorted(registered),
            "invalid_generated_agents": sorted(set(generated_files) - registered),
            "orphan_generated_agents": sorted(registered - tracked),
            "stale_project_references": stale_projects,
            "workspace_only_agents": workspace_only,
        }

    def _agent_files(self) -> list[Path]:
        if not self.generated_dir.is_dir():
            return []
        return sorted(
            path
            for path in self.generated_dir.glob("*.py")
            if path.is_file() and not path.name.startswith("_")
        )

    def _record_invalid(self, path: Path, error: str) -> None:
        self._invalid_records[path.stem] = {
            "agent_name": path.stem,
            "path": str(path),
            "status": "invalid",
            "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
            "last_scanned_at": datetime.now(timezone.utc).isoformat(),
            "validation_ok": False,
            "error": error,
            "source": "dynamic_registry",
        }

    def _is_loadable_agent(self, agent: Any) -> bool:
        name = getattr(agent, "name", None)
        execute = getattr(agent, "execute", None)
        return bool(isinstance(name, str) and name.strip() and inspect.iscoroutinefunction(execute))

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

    def _match_text(
        self,
        module_name: str,
        agent_name: str,
        module: Any,
        agent: Any,
        spec: dict[str, Any] | None,
    ) -> str:
        parts = [module_name, agent_name]
        if spec:
            parts.append(json.dumps(spec, sort_keys=True, ensure_ascii=False))

        for source in (module, agent):
            for attr in ("name", "title", "goal", "target_event", "source", "description"):
                value = getattr(source, attr, None)
                if isinstance(value, (str, int, float, bool)):
                    parts.append(str(value))

        return self._normalize(" ".join(parts))
