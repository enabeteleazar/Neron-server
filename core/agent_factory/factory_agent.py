from __future__ import annotations

import re
import unicodedata
from pathlib import Path
import warnings

from core.agents.base_agent import AgentResult
from core.agent_factory.build_orchestrator import AgentBuildOrchestrator


WORKSPACE = Path("/etc/neron/workspace/agents")


class AgentFactoryAgent:
    """
    Compatibility facade for legacy callers.

    Real agent/tool creation is centralized in AgentBuildOrchestrator so this
    class no longer writes draft files itself.
    """

    async def execute(self, text: str = ""):
        warnings.warn(
            "AgentFactoryAgent is deprecated; use AgentBuildOrchestrator.",
            DeprecationWarning,
            stacklevel=2,
        )
        result = await AgentBuildOrchestrator().build_from_request(
            text,
            requested_by="legacy_agent_factory",
            source_channel="agent_factory",
        )
        project = result.get("project") or {}

        return AgentResult(
            success=result.get("status") == "completed",
            source="agent_factory",
            content=result.get("response") or str(result),
            metadata={
                "compatibility_facade": True,
                "orchestrator": "AgentBuildOrchestrator",
                "project_id": project.get("project_id"),
                "project_status": project.get("status"),
                "registry_status": project.get("registry_status"),
                "created_files": project.get("created_files", []),
            },
        )

    def _extract_name(self, text: str) -> str:

        text = text.lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")

        match = re.search(r"agent (.+)", text)

        if not match:
            return "custom"

        name = match.group(1)

        name = name.replace(" ", "_")
        name = re.sub(r"[^a-z0-9_]", "", name)

        return name or "custom"
