from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agents.factory.registry import DynamicAgentRegistry
from agents.factory.build_orchestrator import AgentBuildOrchestrator
from agents.runtime.runtime import AgentRuntime
from agents.runtime.store import AgentRuntimeStore
from tools.models import ToolSpec
from tools.registry import ToolRegistry
from tools.runtime import ToolRuntime


ROOT = Path(__file__).resolve().parents[1]


def _write_agent(path: Path, name: str, *, valid: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    execute = (
        "    async def execute(self, text=''):\n"
        "        return {'status': 'ok', 'response': text}\n"
        if valid
        else "    def execute(self, text=''):\n        return text\n"
    )
    path.write_text(
        f"class Agent:\n    name = {name!r}\n{execute}",
        encoding="utf-8",
    )


def test_agent_registry_diagnostics_separate_workspace_and_orphans(tmp_path: Path):
    generated = tmp_path / "core" / "agents" / "generated"
    workspace = tmp_path / "workspace" / "agents"
    _write_agent(generated / "tracked_agent.py", "tracked_agent")
    _write_agent(generated / "orphan_agent.py", "orphan_agent")
    _write_agent(generated / "invalid_agent.py", "invalid_agent", valid=False)
    _write_agent(workspace / "draft_agent.py", "draft_agent")

    diagnostics = DynamicAgentRegistry(generated).diagnose_consistency(
        projects=[
            {
                "project_id": "project-tracked",
                "registry_status": "registered",
                "registered_agent": "tracked_agent",
            },
            {
                "project_id": "project-stale",
                "registry_status": "registered",
                "registered_agent": "missing_agent",
            },
        ],
        workspace_agents=workspace,
    )

    assert diagnostics["registered_agents"] == ["orphan_agent", "tracked_agent"]
    assert diagnostics["invalid_generated_agents"] == ["invalid_agent"]
    assert diagnostics["orphan_generated_agents"] == ["orphan_agent"]
    assert diagnostics["workspace_only_agents"] == ["draft_agent"]
    assert diagnostics["stale_project_references"] == [
        {"project_id": "project-stale", "agent": "missing_agent"}
    ]


def test_registry_index_is_computed_without_secondary_file(tmp_path: Path):
    generated = tmp_path / "generated"
    generated.mkdir()
    index = tmp_path / "agent_registry_index.json"
    index.write_text(
        '{"agents":{"removed_agent":{"status":"active","path":"/missing.py"}}}',
        encoding="utf-8",
    )

    registry = DynamicAgentRegistry(generated)
    result = registry.scan()
    computed = registry.validation_index()

    assert result["source"] == "dynamic_registry"
    assert result["agents"] == []
    assert computed["agents"] == {}
    assert "removed_agent" not in computed["agents"]


def test_legacy_runtime_layers_are_removed():
    legacy_paths = (
        "core/agent_factory/promoter.py",
        "core/agent_factory/registry_scanner.py",
        "core/agent_factory/factory_agent.py",
        "core/goal_system/goal_system.py",
        "core/runtime/agents/agent_registry.py",
        "core/runtime/agents/agent_runtime_manager.py",
        "core/runtime/events/event_bus.py",
        "core/runtime/events/event_logger.py",
        "core/runtime/tools/register_tools.py",
        "core/runtime/tools/tool_manager.py",
        "core/task_system/task_store.py",
        "runtime/__init__.py",
    )

    assert [path for path in legacy_paths if (ROOT / path).exists()] == []


@pytest.mark.asyncio
async def test_agent_runtime_emits_events_only_for_registered_agent(
    monkeypatch,
    tmp_path: Path,
):
    generated = tmp_path / "generated"
    _write_agent(generated / "runtime_agent.py", "runtime_agent")
    runtime = AgentRuntime(
        registry=DynamicAgentRegistry(generated),
        tool_registry=ToolRegistry(tmp_path / "tools.json"),
        store=AgentRuntimeStore(tmp_path / "runtime.sqlite3"),
    )
    emitted = []

    async def capture(event):
        emitted.append(event)

    monkeypatch.setattr("agents.runtime.runtime.event_bus.publish", capture)

    success = await runtime.run_agent("runtime_agent", "ok")
    missing = await runtime.run_agent("workspace_only_agent", "no")
    await asyncio.sleep(0)

    assert success.ok is True
    assert missing.ok is False
    assert [event.type for event in emitted] == [
        "agent.execution_started",
        "agent.execution_completed",
    ]


@pytest.mark.asyncio
async def test_tool_runtime_rejects_unregistered_handler_and_emits_events(
    monkeypatch,
    tmp_path: Path,
):
    registry = ToolRegistry(tmp_path / "tools.json")
    runtime = ToolRuntime(
        registry,
        handlers={
            "registered_tool": lambda payload: {
                "ok": True,
                "response": str(payload.get("value") or ""),
            },
            "handler_only_tool": lambda payload: {"ok": True},
        },
    )
    registry.register_tool(
        ToolSpec(
            name="Registered",
            slug="registered_tool",
            description="Registered test tool",
        )
    )
    emitted = []

    async def capture(event):
        emitted.append(event)

    monkeypatch.setattr("tools.runtime.event_bus.publish", capture)

    success = await runtime.execute_tool("registered_tool", {"value": "ok"})
    missing = await runtime.execute_tool("handler_only_tool", {})
    await asyncio.sleep(0)

    assert success.ok is True
    assert missing.error == "tool_not_found"
    assert [event.type for event in emitted] == [
        "tool.execution_started",
        "tool.execution_completed",
    ]


def test_tool_registry_reports_missing_and_workspace_backed_handlers(tmp_path: Path):
    generated = tmp_path / "core" / "tools" / "generated"
    registry = ToolRegistry(tmp_path / "tools.json", generated_dir=generated)
    workspace_handler = tmp_path / "workspace" / "tools" / "active.py"
    workspace_handler.parent.mkdir(parents=True)
    workspace_handler.write_text("def execute(payload): return payload\n", encoding="utf-8")
    registry.register_tool(
        ToolSpec(
            name="Workspace",
            slug="workspace_tool",
            description="Legacy workspace-backed tool",
            metadata={"handler_path": str(workspace_handler)},
        )
    )
    missing_handler = tmp_path / "missing.py"
    missing_handler.write_text("def execute(payload): return payload\n", encoding="utf-8")
    registry.register_tool(
        ToolSpec(
            name="Missing",
            slug="missing_tool",
            description="Missing handler",
            metadata={"handler_path": str(missing_handler)},
        )
    )
    missing_handler.unlink()
    generated.mkdir(parents=True)
    (generated / "orphan_tool.py").write_text(
        "def execute(payload): return payload\n",
        encoding="utf-8",
    )

    diagnostics = registry.diagnose_consistency()

    assert diagnostics["workspace_backed_tools"] == [
        {"tool": "workspace_tool", "path": str(workspace_handler)}
    ]
    assert diagnostics["missing_handlers"] == [
        {"tool": "missing_tool", "path": str(missing_handler)}
    ]
    assert diagnostics["orphan_generated_tools"] == ["orphan_tool"]


def test_tool_registry_rejects_missing_declared_handler(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")

    with pytest.raises(ValueError, match="tool_handler_not_found"):
        registry.register_tool(
            ToolSpec(
                name="Missing",
                slug="missing_tool",
                description="Missing handler",
                metadata={"handler_path": str(tmp_path / "missing.py")},
            )
        )


@pytest.mark.asyncio
async def test_tool_runtime_rejects_workspace_backed_handler(tmp_path: Path):
    handler = tmp_path / "workspace" / "tools" / "legacy.py"
    handler.parent.mkdir(parents=True)
    handler.write_text("def execute(payload): return {'ok': True}\n", encoding="utf-8")
    registry = ToolRegistry(tmp_path / "tools.json")
    registry.register_tool(
        ToolSpec(
            name="Legacy",
            slug="legacy_tool",
            description="Legacy workspace handler",
            metadata={"handler_path": str(handler)},
        )
    )

    result = await ToolRuntime(registry).execute_tool("legacy_tool", {})

    assert result.error == "tool_workspace_handler_rejected"


def test_agent_build_treats_failed_sandbox_payload_as_test_failure(tmp_path: Path):
    builder = AgentBuildOrchestrator(project_root=tmp_path, runtime_check=False)
    result = {
        "returncode": 0,
        "stdout_tail": "",
        "stderr_tail": "",
        "payload": {"ok": False, "error": "pytest sandbox failed"},
    }

    assert builder._test_result_failed(result) is True
    assert builder._test_result_failed(
        {**result, "payload": {"ok": True}}
    ) is False
