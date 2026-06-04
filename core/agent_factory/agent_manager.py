from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.agent_factory.registry import DynamicAgentRegistry
from core.agent_factory.validator import validate_agent
from core.runtime.agents.agent_runtime_manager import get_agent_runtime_manager


DEFAULT_GENERATED_AGENTS = Path("/etc/neron/core/agents/generated")
DEFAULT_WORKSPACE_AGENTS = Path("/etc/neron/workspace/agents")
DEFAULT_WORKSPACE_TESTS = Path("/etc/neron/workspace/agent_tests")
DEFAULT_BACKUPS_DIR = Path("/etc/neron/data/agent_backups")

PROTECTED_AGENTS = {
    "event_countdown_agent",
    "meteo_agent",
    "test_agent",
    "validation_goal_pipeline_agent",
}


class AgentManager:
    def __init__(
        self,
        *,
        generated_agents: Path = DEFAULT_GENERATED_AGENTS,
        workspace_agents: Path = DEFAULT_WORKSPACE_AGENTS,
        workspace_tests: Path = DEFAULT_WORKSPACE_TESTS,
        backups_dir: Path = DEFAULT_BACKUPS_DIR,
        runtime_manager: Any | None = None,
    ) -> None:
        self.generated_agents = generated_agents
        self.workspace_agents = workspace_agents
        self.workspace_tests = workspace_tests
        self.backups_dir = backups_dir
        self.runtime_manager = runtime_manager or get_agent_runtime_manager()

    def list_managed_agents(self) -> dict[str, Any]:
        records = self._registry().list_agent_records()
        agents = [self._status_from_record(record) for record in sorted(records, key=lambda item: str(item.get("module_name")))]
        return {"status": "ok", "count": len(agents), "agents": agents}

    def get_agent_status(self, agent_name: str) -> dict[str, Any]:
        name = self._normalize_agent_name(agent_name)
        path = self._agent_path(name)
        if not path.exists():
            return {"status": "not_found", "agent": name, "exists": False}

        record = self._record_for(name)
        validation = validate_agent(str(path))
        runtime_state = self.runtime_manager.get_state(name)
        return {
            "status": "ok",
            "agent": name,
            "exists": True,
            "protected": self._is_protected(name),
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": self._sha256(path),
            "validation": validation,
            "registry": record,
            "runtime_state": runtime_state,
            "backups": self._list_backups(name),
        }

    def backup_agent(self, agent_name: str) -> dict[str, Any]:
        name = self._normalize_agent_name(agent_name)
        path = self._agent_path(name)
        if not path.exists():
            return {"status": "not_found", "agent": name, "backup_created": False}

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target_dir = self.backups_dir / name
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / f"{timestamp}_{path.name}"
        shutil.copy2(path, destination)
        return {
            "status": "ok",
            "agent": name,
            "backup_created": True,
            "backup_path": str(destination),
            "source_path": str(path),
            "sha256": self._sha256(destination),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def inspect_agent(self, agent_name: str) -> dict[str, Any]:
        status = self.get_agent_status(agent_name)
        if status.get("status") != "ok":
            return status

        path = Path(str(status["path"]))
        content = path.read_text(encoding="utf-8")
        return {
            **status,
            "source_preview": content[:4000],
            "lines": len(content.splitlines()),
            "contains_agent_class": "class Agent" in content,
            "contains_execute": "async def execute" in content,
        }

    def delete_agent(self, agent_name: str) -> dict[str, Any]:
        name = self._normalize_agent_name(agent_name)
        if self._is_protected(name):
            return {
                "status": "refused",
                "agent": name,
                "reason": "protected_agent",
                "protected": True,
                "deleted": False,
            }

        path = self._agent_path(name)
        if not path.exists():
            return {"status": "not_found", "agent": name, "deleted": False}

        backup = self.backup_agent(name)
        if backup.get("backup_created") is not True:
            return {
                "status": "failed",
                "agent": name,
                "reason": "backup_required",
                "backup": backup,
                "deleted": False,
            }

        path.unlink()
        runtime_reload = self.runtime_manager.reload()
        return {
            "status": "deleted",
            "agent": name,
            "deleted": True,
            "backup": backup,
            "runtime_reload": runtime_reload,
        }

    def revise_agent(self, agent_name: str) -> dict[str, Any]:
        return self._not_implemented(agent_name, "revise")

    def update_agent(self, agent_name: str, request: str = "") -> dict[str, Any]:
        return self._not_implemented(agent_name, "update", request=request)

    def rename_agent(self, agent_name: str, new_name: str = "") -> dict[str, Any]:
        name = self._normalize_agent_name(agent_name)
        if self._is_protected(name):
            return {"status": "refused", "agent": name, "reason": "protected_agent", "protected": True}
        return self._not_implemented(name, "rename", new_name=new_name)

    def rollback_agent(self, agent_name: str, backup_path: str | None = None) -> dict[str, Any]:
        return self._not_implemented(agent_name, "rollback", backup_path=backup_path)

    def _not_implemented(self, agent_name: str, action: str, **extra: Any) -> dict[str, Any]:
        return {
            "status": "not_implemented",
            "action": action,
            "agent": self._normalize_agent_name(agent_name),
            **extra,
        }

    def _status_from_record(self, record: dict[str, Any]) -> dict[str, Any]:
        name = str(record.get("module_name") or record.get("agent_name") or "")
        path = Path(str(record.get("path") or self._agent_path(name)))
        return {
            "agent": name,
            "agent_name": record.get("agent_name"),
            "path": str(path),
            "protected": self._is_protected(name),
            "exists": path.exists(),
            "spec": record.get("spec"),
            "spec_signature": record.get("spec_signature"),
        }

    def _registry(self) -> DynamicAgentRegistry:
        return DynamicAgentRegistry(self.generated_agents)

    def _record_for(self, agent_name: str) -> dict[str, Any] | None:
        for record in self._registry().list_agent_records():
            if str(record.get("module_name") or "") == agent_name:
                return record
        return None

    def _agent_path(self, agent_name: str) -> Path:
        return self.generated_agents / f"{agent_name}.py"

    def _normalize_agent_name(self, agent_name: str) -> str:
        return Path(str(agent_name).strip()).stem

    def _is_protected(self, agent_name: str) -> bool:
        return agent_name in PROTECTED_AGENTS

    def _list_backups(self, agent_name: str) -> list[dict[str, Any]]:
        backup_dir = self.backups_dir / agent_name
        if not backup_dir.exists():
            return []
        backups = []
        for path in sorted(backup_dir.glob("*.py"), reverse=True):
            backups.append(
                {
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "sha256": self._sha256(path),
                }
            )
        return backups

    def _sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
