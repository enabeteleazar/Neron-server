from __future__ import annotations

from typing import Any

from core.code_awareness.dependency_mapper import DependencyMapper
from core.code_awareness.scanner import CodeScanner


ARCHITECTURE_GROUPS = {
    "Communication": [
        "core/agents/communication",
        "core/gateway",
    ],
    "Cognition": [
        "core/cognitive",
        "core/cognitive_core",
        "core/planning",
        "core/goals",
        "core/goal_system",
        "core/task_system",
    ],
    "Memoire": [
        "core/memory",
    ],
    "SelfModel": [
        "core/self_model",
    ],
    "WorldModel": [
        "core/world_model",
        "core/memory/world_model",
    ],
    "Runtime": [
        "core/runtime",
        "core/control_plane",
        "core/service_core",
    ],
    "Agents": [
        "core/agents/automation",
        "core/agents/core",
        "core/agents/dev",
        "core/agents/io",
        "agents",
    ],
    "API": [
        "core/api",
        "core/app.py",
    ],
}


class ArchitectureMapper:
    def __init__(
        self,
        scanner: CodeScanner | None = None,
        dependency_mapper: DependencyMapper | None = None,
    ) -> None:
        self.scanner = scanner or CodeScanner()
        self.dependency_mapper = dependency_mapper or DependencyMapper(self.scanner)

    def map(self) -> dict[str, Any]:
        scan = self.scanner.scan(max_depth=2)
        files = self.scanner.iter_files()
        dependency_map = self.dependency_mapper.map(max_files=250)

        groups = []
        for name, prefixes in ARCHITECTURE_GROUPS.items():
            matching_files = [
                str(path.relative_to(self.scanner.root))
                for path in files
                if any(str(path.relative_to(self.scanner.root)).startswith(prefix) for prefix in prefixes)
            ]

            groups.append(
                {
                    "name": name,
                    "packages": prefixes,
                    "files": len(matching_files),
                    "sample_files": matching_files[:12],
                }
            )

        return {
            "name": "Neron",
            "summary": {
                "files": scan["files"],
                "modules": scan["modules"],
                "packages": len(scan["packages"]),
                "architecture_known": True,
            },
            "groups": groups,
            "key_flows": [
                ["TelegramAgent", "GoalOrchestrator", "Planner", "TaskExecutor", "PlanExecutor"],
                ["FastAPI", "IntentRouter", "AgentRouter", "Agents"],
                ["SelfModel", "Runtime", "Services", "Diagnostics"],
            ],
            "dependencies": dependency_map["summary"],
        }


def map_architecture() -> dict[str, Any]:
    return ArchitectureMapper().map()
