from __future__ import annotations

import re
import unicodedata
import unicodedata
from pathlib import Path

from core.agents.base_agent import AgentResult
from core.agent_factory.validator import validate_agent


WORKSPACE = Path("/etc/neron/workspace/agents")


class AgentFactoryAgent:

    async def execute(self, text: str = ""):

        WORKSPACE.mkdir(parents=True, exist_ok=True)

        name = self._extract_name(text)

        filename = f"{name}_agent.py"

        path = WORKSPACE / filename

        code = f'''class Agent:

    async def execute(self, text: str = ""):
        return {{
            "response": "Agent {name} exécuté"
        }}
'''

        path.write_text(code, encoding="utf-8")

        validation = validate_agent(str(path))

        return AgentResult(
            success=True,
            source="agent_factory",
            content=(
                f"Agent brouillon créé : {path}\n"
                f"Validation : {'OK' if validation['ok'] else validation['error']}\n"
                f"Promotion manuelle requise."
            ),
            metadata={
                "workspace_path": str(path),
                "validation": validation,
                "promotion_required": True,
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
