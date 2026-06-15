from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from modules.capabilities.matcher import CapabilityMatcher
from modules.capabilities.models import Capability, CapabilityRequest
from modules.capabilities.registry import CapabilityRegistry
from modules.capabilities.resolver import CapabilityResolver
from tools.code_generator import ToolCodeGenerator, validate_generated_code
from tools.creator import ToolCreator
from tools.models import ToolNeed, ToolResult, ToolSpec
from tools.registry import ToolRegistry
from tools.runtime import ToolRuntime
from tools.spec_builder import ToolSpecBuilder
from tools.templates import deterministic_tool_code


class EmptyAgentRegistry:
    def list_agent_records(self):
        return []


class EmptyProjectManager:
    def list_projects(self, status=None, limit=100):
        return []


class FakeGoalManager:
    def __init__(self):
        self.created = []

    def create_goal(self, **kwargs):
        self.created.append(kwargs)
        return {"id": "goal-tool-v2"}

    def update_status(self, goal_id, status, **kwargs):
        return {"id": goal_id, "status": status}


class FakeExecutionEngine:
    def __init__(self):
        self.enqueued = []

    def enqueue_goal(self, goal_id, title, source, metadata):
        self.enqueued.append((goal_id, title, source, metadata))
        return {"goal_id": goal_id, "status": "queued"}


class FakeRunner:
    def submit(self, **kwargs):
        self.submitted = kwargs


class FailingGenerator(ToolCodeGenerator):
    def __init__(self):
        self.calls = 0

    def can_generate(self, need):
        return True

    async def generate_tool_code(self, spec, need):
        self.calls += 1
        raise RuntimeError("deterministic failed")

    async def generate_tests(self, spec, need):
        raise AssertionError("test generation must not run")


class MockCodexGenerator(ToolCodeGenerator):
    def __init__(self):
        self.code_calls = []
        self.test_calls = []

    def can_generate(self, need):
        return True

    async def generate_tool_code(self, spec, need):
        self.code_calls.append(spec.slug)
        return deterministic_tool_code(spec, need)

    async def generate_tests(self, spec, need):
        self.test_calls.append(spec.slug)
        return "def test_generated():\n    assert True\n"


class DangerousGenerator(ToolCodeGenerator):
    def can_generate(self, need):
        return True

    async def generate_tool_code(self, spec, need):
        return (
            "import subprocess\n"
            "from tools.models import ToolResult\n"
            "def execute(payload):\n"
            "    subprocess.run(['true'])\n"
            "    return ToolResult(ok=True, response='unsafe')\n"
        )

    async def generate_tests(self, spec, need):
        return "def test_generated():\n    assert True\n"


class DisabledGenerator(ToolCodeGenerator):
    def can_generate(self, need):
        return False

    async def generate_tool_code(self, spec, need):
        raise AssertionError("disabled")

    async def generate_tests(self, spec, need):
        raise AssertionError("disabled")


def need(domain: str, intent: str) -> ToolNeed:
    return ToolNeed(
        request_text=f"{intent} {domain}",
        domain=domain,
        intent=intent,
        capability_goal=f"{intent} le domaine {domain}",
        expected_outputs=["status", "summary", "issues", "recommendation"],
        safety_level="low",
    )


@pytest.mark.parametrize(
    ("domain", "intent", "slugs"),
    [
        (
            "backups",
            "analyze",
            [
                "backup_reader_tool",
                "backup_analyzer_tool",
                "backup_summary_tool",
            ],
        ),
        (
            "sqlite",
            "analyze",
            [
                "sqlite_reader_tool",
                "sqlite_analyzer_tool",
                "sqlite_summary_tool",
            ],
        ),
        (
            "systemd",
            "diagnose",
            [
                "systemd_status_tool",
                "systemd_diagnosis_tool",
                "systemd_summary_tool",
            ],
        ),
    ],
)
def test_spec_builder_creates_generic_intent_plan(domain, intent, slugs):
    specs = ToolSpecBuilder().build_specs_from_need(need(domain, intent))

    assert [spec.slug for spec in specs] == slugs
    assert all(spec.safety["payload_only"] is True for spec in specs)
    assert all(spec.safety["allow_system_commands"] is False for spec in specs)


@pytest.mark.asyncio
async def test_deterministic_creation_registers_and_executes_tools(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")
    runtime = ToolRuntime(registry)
    creator = ToolCreator(
        registry,
        runtime,
        workspace=tmp_path / "workspace" / "tools",
    )

    result = await creator.create_from_need(need("backups", "analyze"))

    assert result["status"] == "completed"
    assert result["creation_strategy"] == "deterministic"
    assert result["created_tools"] == [
        "backup_reader_tool",
        "backup_analyzer_tool",
        "backup_summary_tool",
    ]
    first = await runtime.execute_tool(
        "backup_reader_tool",
        {"items": ["backup ok", "backup corrupted"]},
    )
    second = await runtime.execute_tool(
        "backup_analyzer_tool",
        first.data,
    )
    final = await runtime.execute_tool(
        "backup_summary_tool",
        second.data,
    )
    assert first.ok and second.ok and final.ok
    assert second.data["issue_count"] == 1
    assert final.data["recommendation"]
    assert all(
        registry.get_tool(slug).source == "tool_creator_deterministic"
        for slug in result["created_tools"]
    )


@pytest.mark.asyncio
async def test_generated_handler_can_reload_from_registry(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")
    creator = ToolCreator(
        registry,
        ToolRuntime(registry),
        workspace=tmp_path / "workspace" / "tools",
    )
    await creator.create_from_need(need("sqlite", "analyze"))

    reloaded_registry = ToolRegistry(tmp_path / "tools.json")
    reloaded_runtime = ToolRuntime(reloaded_registry)
    result = await reloaded_runtime.execute_tool(
        "sqlite_analyzer_tool",
        {"items": ["ok", "invalid database"]},
    )

    assert result.ok is True
    assert result.data["issue_count"] == 1


@pytest.mark.asyncio
async def test_existing_tools_are_reused(tmp_path: Path):
    creator = ToolCreator(
        ToolRegistry(tmp_path / "tools.json"),
        workspace=tmp_path / "workspace" / "tools",
    )

    first = await creator.create_from_need(need("backups", "analyze"))
    second = await creator.create_from_need(need("backups", "analyze"))

    assert len(first["created_tools"]) == 3
    assert second["created_tools"] == []
    assert second["reused_tools"] == first["required_tools"]


@pytest.mark.asyncio
async def test_codex_fallback_is_injected_and_mocked(tmp_path: Path):
    deterministic = FailingGenerator()
    codex = MockCodexGenerator()
    creator = ToolCreator(
        ToolRegistry(tmp_path / "tools.json"),
        workspace=tmp_path / "workspace" / "tools",
        deterministic_generator=deterministic,
        codex_generator=codex,
    )

    result = await creator.create_from_need(need("backups", "count"))

    assert result["status"] == "completed"
    assert result["creation_strategy"] == "codex_required"
    assert deterministic.calls == 2
    assert codex.code_calls == result["created_tools"]
    assert codex.test_calls == result["created_tools"]
    assert all(
        creator.registry.get_tool(slug).source == "tool_creator_codex"
        for slug in result["created_tools"]
    )


def test_dangerous_generated_code_is_rejected():
    errors = validate_generated_code(
        "import os\n"
        "from tools.models import ToolResult\n"
        "def execute(payload):\n"
        "    open('/tmp/value', 'w')\n"
        "    return ToolResult(ok=True)\n"
    )

    assert "forbidden_import:os" in errors
    assert "forbidden_call:open" in errors


@pytest.mark.asyncio
async def test_creator_does_not_promote_dangerous_code(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")
    creator = ToolCreator(
        registry,
        workspace=tmp_path / "workspace" / "tools",
        deterministic_generator=DangerousGenerator(),
        codex_generator=DisabledGenerator(),
    )

    result = await creator.create_from_need(need("backups", "count"))

    assert result["status"] == "failed"
    assert registry.list_tools() == []
    assert "forbidden_import:subprocess" in result["errors"][0]


@pytest.mark.asyncio
async def test_resolver_create_agent_prepares_generic_tools(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")
    creator = ToolCreator(
        registry,
        workspace=tmp_path / "workspace" / "tools",
    )
    goals = FakeGoalManager()
    resolver = CapabilityResolver(
        registry=CapabilityRegistry(
            agent_registry=EmptyAgentRegistry(),
            project_manager=EmptyProjectManager(),
            builtins=[],
        ),
        matcher=CapabilityMatcher(tool_registry=registry),
        goal_manager=goals,
        execution_engine=FakeExecutionEngine(),
        background_runner=FakeRunner(),
        tool_creator=creator,
    )

    result = await resolver.resolve(
        CapabilityRequest(text="Analyse les sauvegardes Néron")
    )

    assert result is not None
    assert result.decision.decision == "create_agent"
    metadata = goals.created[0]["metadata"]
    assert metadata["required_tools"] == [
        "backup_reader_tool",
        "backup_analyzer_tool",
        "backup_summary_tool",
    ]
    assert metadata["tool_creation_status"] == "ready"


@pytest.mark.asyncio
async def test_resolver_existing_agent_missing_tool_creates_only_missing_tool(
    tmp_path: Path,
):
    tool_registry = ToolRegistry(tmp_path / "tools.json")
    creator = ToolCreator(
        tool_registry,
        workspace=tmp_path / "workspace" / "tools",
    )
    capability = Capability(
        slug="backup_agent",
        name="Backup agent",
        capability_type="agent",
        source="runtime_agent",
        description="Analyse les sauvegardes Néron",
        aliases=["analyse les sauvegardes neron"],
        agent_slug="backup_agent",
        metadata={"spec": {"required_tools": ["backup_integrity_tool"]}},
    )
    goals = FakeGoalManager()
    resolver = CapabilityResolver(
        registry=CapabilityRegistry(
            agent_registry=EmptyAgentRegistry(),
            project_manager=EmptyProjectManager(),
            builtins=[capability],
        ),
        matcher=CapabilityMatcher(tool_registry=tool_registry),
        goal_manager=goals,
        execution_engine=FakeExecutionEngine(),
        background_runner=FakeRunner(),
        tool_creator=creator,
    )

    result = await resolver.resolve(
        CapabilityRequest(text="Analyse les sauvegardes Néron")
    )

    assert result.decision.decision == "create_tool"
    assert goals.created[0]["metadata"]["required_tools"] == [
        "backup_integrity_tool"
    ]
    assert tool_registry.tool_exists("backup_integrity_tool")
    spec = tool_registry.get_tool("backup_integrity_tool")
    assert spec.metadata["required_by_capability"] == "backup_agent"


@pytest.mark.asyncio
async def test_resolver_create_tool_uses_generic_tool_creator(tmp_path: Path):
    tool_registry = ToolRegistry(tmp_path / "tools.json")
    creator = ToolCreator(
        tool_registry,
        workspace=tmp_path / "workspace" / "tools",
    )
    goals = FakeGoalManager()
    resolver = CapabilityResolver(
        registry=CapabilityRegistry(
            agent_registry=EmptyAgentRegistry(),
            project_manager=EmptyProjectManager(),
            builtins=[],
        ),
        matcher=CapabilityMatcher(tool_registry=tool_registry),
        goal_manager=goals,
        execution_engine=FakeExecutionEngine(),
        background_runner=FakeRunner(),
        tool_creator=creator,
    )

    result = await resolver.resolve(
        CapabilityRequest(text="Combien de sauvegardes sont valides ?")
    )

    assert result.decision.decision == "create_tool"
    assert goals.created[0]["metadata"]["required_tools"] == [
        "backup_reader_tool",
        "backup_counter_tool",
    ]


@pytest.mark.asyncio
async def test_tool_creator_v2_endpoints(monkeypatch, tmp_path: Path):
    from core.tools import routes

    creator = ToolCreator(
        ToolRegistry(tmp_path / "tools.json"),
        workspace=tmp_path / "workspace" / "tools",
    )
    monkeypatch.setattr(routes, "get_tool_creator", lambda: creator)
    app = FastAPI()
    app.include_router(routes.router)

    async def allow_test_request():
        return None

    app.dependency_overrides[routes.verify_api_key] = allow_test_request
    payload = {
        "text": "Analyse les sauvegardes Néron",
        "domain": "backups",
        "intent": "analyze",
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        plan = await client.post("/tools/plan", json=payload)
        created = await client.post("/tools/create-from-need", json=payload)

    assert plan.status_code == 200
    assert plan.json()["required_tools"] == [
        "backup_reader_tool",
        "backup_analyzer_tool",
        "backup_summary_tool",
    ]
    assert plan.json()["creation_strategy"] == "deterministic"
    assert created.status_code == 200
    assert created.json()["status"] == "completed"
