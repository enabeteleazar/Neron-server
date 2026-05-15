from __future__ import annotations

import importlib.util
from pathlib import Path


AGENT_REGISTRY = {}


class DynamicAgentRegistry:

    def __init__(self):
        self.generated_dir = Path("/etc/neron/core/agents/generated")

    def load_generated_agents(self):
        AGENT_REGISTRY.clear()

        if not self.generated_dir.exists():
            return

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
                AGENT_REGISTRY[module_name] = module.Agent()
