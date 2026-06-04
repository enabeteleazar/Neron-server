from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import inspect
import json
import py_compile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.runtime.agents.agent_runtime_manager import get_agent_runtime_manager


DEFAULT_GENERATED_AGENTS = Path("/etc/neron/core/agents/generated")
DEFAULT_REGISTRY_INDEX = Path("/etc/neron/data/agent_registry_index.json")
DEFAULT_QUARANTINE_DIR = Path("/etc/neron/data/agent_quarantine")


class AgentRegistryScanner:
    def __init__(
        self,
        *,
        generated_agents: Path | str = DEFAULT_GENERATED_AGENTS,
        index_path: Path | str = DEFAULT_REGISTRY_INDEX,
        quarantine_dir: Path | str = DEFAULT_QUARANTINE_DIR,
        runtime_manager: Any | None = None,
    ) -> None:
        self.generated_agents = Path(generated_agents)
        self.index_path = Path(index_path)
        self.quarantine_dir = Path(quarantine_dir)
        self.runtime_manager = runtime_manager or get_agent_runtime_manager()

    def load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"agents": {}}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return {"agents": {}}
        if not isinstance(data, dict):
            return {"agents": {}}
        agents = data.get("agents")
        return {**data, "agents": agents if isinstance(agents, dict) else {}}

    async def scan(self) -> dict[str, Any]:
        index = self.load_index()
        agents = dict(index.get("agents") or {})
        scanned_at = self._now()
        changed_active = False
        scanned: list[dict[str, Any]] = []

        for path in self._agent_files():
            checksum = self._checksum(path)
            previous = agents.get(path.stem) or {}
            if previous.get("checksum") == checksum and previous.get("status") == "active":
                entry = {**previous, "last_scanned_at": scanned_at}
            else:
                validation = await self._validate_agent_file(path)
                entry = {
                    "agent_name": validation.get("agent_name") or path.stem,
                    "path": str(path),
                    "status": "active" if validation["ok"] else "invalid",
                    "checksum": checksum,
                    "last_scanned_at": scanned_at,
                    "validation_ok": validation["ok"],
                    "error": validation.get("error"),
                    "source": "generated_scan",
                }
                if validation["ok"] and (
                    previous.get("checksum") != checksum
                    or previous.get("status") != "active"
                ):
                    changed_active = True
            agents[path.stem] = entry
            scanned.append(entry)

        index = {"agents": agents, "last_scanned_at": scanned_at}
        self._save_index(index)

        runtime_reload = None
        if changed_active:
            runtime_reload = self.runtime_manager.reload()

        return {
            "status": "ok",
            "scanned": len(scanned),
            "active": len([item for item in scanned if item.get("status") == "active"]),
            "invalid": len([item for item in scanned if item.get("status") == "invalid"]),
            "runtime_reloaded": bool(runtime_reload),
            "runtime_reload": runtime_reload,
            "agents": scanned,
        }

    def get_index(self) -> dict[str, Any]:
        return self.load_index()

    def index(self) -> dict[str, Any]:
        return self.get_index()

    def _agent_files(self) -> list[Path]:
        if not self.generated_agents.exists():
            return []
        return sorted(
            path
            for path in self.generated_agents.glob("*.py")
            if path.is_file() and path.name != "__init__.py" and not path.name.startswith("__pycache__")
        )

    async def _validate_agent_file(self, path: Path) -> dict[str, Any]:
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            return {"ok": False, "error": f"py_compile_failed: {exc}"}

        try:
            module = self._load_module(path)
        except Exception as exc:
            return {"ok": False, "error": f"import_failed: {exc}"}

        agent_class = getattr(module, "Agent", None)
        if agent_class is None:
            return {"ok": False, "error": "class Agent manquante"}

        name = getattr(agent_class, "name", None)
        try:
            agent = agent_class()
        except Exception as exc:
            return {"ok": False, "error": f"agent_init_failed: {exc}"}

        name = name or getattr(agent, "name", None)
        if not isinstance(name, str) or not name.strip():
            return {"ok": False, "error": "attribut name manquant"}

        execute = getattr(agent, "execute", None)
        if execute is None or not inspect.iscoroutinefunction(execute):
            return {"ok": False, "error": "méthode async execute manquante"}

        try:
            await asyncio.wait_for(execute(text="smoke test"), timeout=5)
        except Exception as exc:
            return {"ok": False, "error": f"smoke_failed: {exc}"}

        return {"ok": True, "agent_name": name}

    def _load_module(self, path: Path) -> Any:
        spec = importlib.util.spec_from_file_location(f"generated_scan.{path.stem}", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("module spec introuvable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _save_index(self, index: dict[str, Any]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    def _checksum(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
