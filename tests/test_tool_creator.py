from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from fastapi import FastAPI

from core.agent_factory.build_orchestrator import AgentBuildOrchestrator
from core.capabilities.models import CapabilityRequest
from core.capabilities.registry import CapabilityRegistry
from core.capabilities.resolver import CapabilityResolver
from core.tools.creator import LOG_TOOL_SLUGS, ToolCreator
from core.tools.models import ToolResult, ToolSpec
from core.tools.registry import ToolRegistry
from core.tools.runtime import ToolRuntime
from core.scheduler.scheduler import TaskScheduler
from core.scheduler.store import SchedulerStore


LOG_REQUEST = "Analyse automatiquement les logs Néron et résume les erreurs critiques"


class EmptyAgentRegistry:
    def list_agent_records(self):
        return []


class EmptyProjectManager:
    def list_projects(self, status=None, limit=100):
        return []


class FakeGoalManager:
    def __init__(self) -> None:
        self.created = []

    def create_goal(self, **kwargs):
        self.created.append(kwargs)
        return {"id": "goal-tools", "metadata": kwargs["metadata"]}

    def update_status(self, goal_id, status, **kwargs):
        return {"id": goal_id, "status": status}


class FakeExecutionEngine:
    def __init__(self) -> None:
        self.enqueued = []

    def enqueue_goal(self, goal_id, title, source, metadata):
        self.enqueued.append((goal_id, title, source, metadata))
        return {"goal_id": goal_id, "status": "queued"}


class FakeRunner:
    def submit(self, **kwargs):
        self.submitted = kwargs


def make_creator(tmp_path: Path) -> ToolCreator:
    registry = ToolRegistry(tmp_path / "tools.json")
    return ToolCreator(registry=registry)


def test_tool_creator_plans_three_log_tools(tmp_path: Path):
    creator = make_creator(tmp_path)

    specs = creator.plan_tools_for_request(LOG_REQUEST)

    assert [spec.slug for spec in specs] == list(LOG_TOOL_SLUGS)
    assert all(spec.safety["allow_system_commands"] is False for spec in specs)


def test_tool_registry_registers_and_finds_tool(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")
    spec = ToolSpec(
        name="Mock tool",
        slug="mock_tool",
        description="Tool de test",
        safety={"allow_system_commands": False},
    )

    registry.register_tool(spec)

    assert registry.tool_exists("mock_tool") is True
    assert registry.get_tool("mock_tool") == spec
    assert registry.find_tool_for_request("utilise le mock tool") == spec


async def test_tool_runtime_executes_mock_tool(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")
    registry.register_tool(
        ToolSpec(
            name="Mock tool",
            slug="mock_tool",
            description="Tool de test",
            safety={"allow_system_commands": False},
        )
    )
    runtime = ToolRuntime(
        registry,
        handlers={
            "mock_tool": lambda payload: ToolResult(
                ok=True,
                response=f"valeur={payload['value']}",
                data=payload,
            )
        },
    )

    result = await runtime.execute_tool("mock_tool", {"value": 42})

    assert result.ok is True
    assert result.response == "valeur=42"


def test_tool_creator_does_not_recreate_existing_tool(tmp_path: Path):
    creator = make_creator(tmp_path)

    first = creator.ensure_tools_for_request(LOG_REQUEST)
    second = creator.ensure_tools_for_request(LOG_REQUEST)

    assert first["created_tools"] == list(LOG_TOOL_SLUGS)
    assert second["created_tools"] == []
    assert second["existing_tools"] == list(LOG_TOOL_SLUGS)


async def test_log_tool_pipeline_returns_business_response(tmp_path: Path):
    creator = make_creator(tmp_path)

    result = await creator.execute_tools_for_request(
        LOG_REQUEST,
        {
            "logs": [
                "INFO component=api démarrage",
                "ERROR component=resolver timeout",
                "CRITICAL [runtime] exécution impossible",
            ]
        },
    )

    assert result.ok is True
    normalized = result.response.lower()
    assert "log" in normalized or "erreur" in normalized
    for marker in (
        "demande traitée",
        "agent disponible",
        "je suis un agent",
        "réponse déterministe",
    ):
        assert marker not in normalized
    assert result.data["error_count"] == 2


async def test_log_summary_runtime_reads_nested_payload_errors(tmp_path: Path):
    creator = make_creator(tmp_path)
    creator.ensure_tools_for_request(LOG_REQUEST)

    result = await creator.runtime.execute_tool(
        "neron_log_summary_tool",
        {
            "payload": {
                "errors": [
                    "ERROR core failed",
                    "CRITICAL planner timeout",
                ]
            }
        },
    )

    assert result.ok is True
    assert result.data["error_count"] == 2
    assert result.data["severity"] == "critical"
    assert set(result.data["components"]) >= {"core", "planner"}
    assert "ERROR core failed" in result.data["excerpt"]
    assert result.data["recommendation"]


def test_log_agent_template_is_specialized_when_tools_are_ready(tmp_path: Path):
    builder = AgentBuildOrchestrator(
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "tests",
        generated_agents=tmp_path / "generated",
        runtime_check=False,
    )
    spec = builder.plan_spec(
        "Créer un agent durable qui analyse automatiquement les logs Néron"
    )

    builder._tools_ready_for_build = True
    agent_file = builder._write_agent(spec)
    content = agent_file.read_text(encoding="utf-8")

    assert "Analyse des logs Néron" in content
    assert "Demande traitée" not in content


async def test_capability_resolver_prepares_tools_before_agent_goal(tmp_path: Path):
    creator = make_creator(tmp_path)
    scheduler = TaskScheduler(
        store=SchedulerStore(tmp_path / "scheduler.sqlite3"),
        tool_runtime=creator.runtime,
    )
    goals = FakeGoalManager()
    engine = FakeExecutionEngine()
    resolver = CapabilityResolver(
        registry=CapabilityRegistry(
            agent_registry=EmptyAgentRegistry(),
            project_manager=EmptyProjectManager(),
            builtins=[],
        ),
        goal_manager=goals,
        execution_engine=engine,
        background_runner=FakeRunner(),
        tool_creator=creator,
        task_scheduler=scheduler,
    )

    result = await resolver.resolve(
        CapabilityRequest(text=LOG_REQUEST, channel="telegram")
    )

    assert result is not None
    assert result.decision is not None
    assert result.decision.decision == "create_agent"
    metadata = goals.created[0]["metadata"]
    assert metadata["required_tools"] == list(LOG_TOOL_SLUGS)
    assert metadata["created_tools"] == list(LOG_TOOL_SLUGS)
    assert metadata["tool_creation_status"] == "ready"
    assert all(creator.registry.tool_exists(slug) for slug in LOG_TOOL_SLUGS)
    assert engine.enqueued[0][3]["required_tools"] == list(LOG_TOOL_SLUGS)
    assert len(metadata["scheduler_task_ids"]) == 3
    assert metadata["task_id"] == metadata["scheduler_task_ids"][0]
    assert metadata["composite_task_id"]
    tasks = [scheduler.get_task(task_id) for task_id in metadata["scheduler_task_ids"]]
    assert tasks[0].depends_on == []
    assert tasks[1].depends_on == [tasks[0].task_id]
    assert tasks[2].depends_on == [tasks[1].task_id]
    composite = scheduler.get_task(metadata["composite_task_id"])
    assert composite.kind == "composite"
    assert composite.depends_on == [tasks[2].task_id]


async def test_capability_resolver_uses_tool_creator_for_create_tool(tmp_path: Path):
    creator = make_creator(tmp_path)
    scheduler = TaskScheduler(
        store=SchedulerStore(tmp_path / "scheduler.sqlite3"),
        tool_runtime=creator.runtime,
    )
    goals = FakeGoalManager()
    resolver = CapabilityResolver(
        registry=CapabilityRegistry(
            agent_registry=EmptyAgentRegistry(),
            project_manager=EmptyProjectManager(),
            builtins=[],
        ),
        goal_manager=goals,
        execution_engine=FakeExecutionEngine(),
        background_runner=FakeRunner(),
        tool_creator=creator,
        task_scheduler=scheduler,
    )

    result = await resolver.resolve(
        CapabilityRequest(
            text="Analyse les logs Néron et résume les erreurs critiques",
            channel="telegram",
        )
    )

    assert result is not None
    assert result.decision is not None
    assert result.decision.decision == "create_tool"
    assert goals.created[0]["metadata"]["required_tools"] == list(LOG_TOOL_SLUGS)


async def test_capability_log_chain_runs_in_background_worker(tmp_path: Path):
    creator = make_creator(tmp_path)
    scheduler = TaskScheduler(
        store=SchedulerStore(tmp_path / "scheduler.sqlite3"),
        tool_runtime=creator.runtime,
        worker_enabled=True,
        worker_poll_interval=0.01,
    )
    goals = FakeGoalManager()
    resolver = CapabilityResolver(
        registry=CapabilityRegistry(
            agent_registry=EmptyAgentRegistry(),
            project_manager=EmptyProjectManager(),
            builtins=[],
        ),
        goal_manager=goals,
        execution_engine=FakeExecutionEngine(),
        background_runner=FakeRunner(),
        tool_creator=creator,
        task_scheduler=scheduler,
    )

    try:
        await scheduler.start_worker()
        result = await resolver.resolve(
            CapabilityRequest(
                text=LOG_REQUEST,
                channel="telegram",
                metadata={
                    "payload": {
                        "logs": [
                            "ERROR core failed",
                            "CRITICAL planner timeout",
                        ]
                    }
                },
            )
        )
        composite_id = result.metadata["composite_task_id"]
        for _ in range(200):
            composite = scheduler.get_task(composite_id)
            if composite.status == "completed":
                break
            await asyncio.sleep(0.01)
    finally:
        await scheduler.stop_worker()

    assert result.async_started is True
    assert result.metadata["task_id"]
    assert composite.status == "completed"
    assert composite.result["data"]["error_count"] == 2
    assert composite.result["data"]["severity"] == "critical"


async def test_tool_endpoints_list_get_and_execute(tmp_path: Path, monkeypatch):
    from core.tools import routes

    creator = make_creator(tmp_path)
    creator.ensure_tools_for_request(LOG_REQUEST)
    monkeypatch.setattr(routes, "get_tool_registry", lambda: creator.registry)
    monkeypatch.setattr(routes, "get_tool_runtime", lambda: creator.runtime)
    app = FastAPI()
    app.include_router(routes.router)

    async def allow_test_request():
        return None

    app.dependency_overrides[routes.verify_api_key] = allow_test_request

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        listed = await client.get("/tools")
        fetched = await client.get("/tools/neron_log_summary_tool")
        executed = await client.post(
            "/tools/neron_log_summary_tool/execute",
            json={"payload": {"errors": ["ERROR component=api timeout"]}},
        )

    assert listed.status_code == 200
    assert listed.json()["count"] == 3
    assert fetched.status_code == 200
    assert executed.status_code == 200
    assert executed.json()["ok"] is True


async def test_log_summary_endpoint_accepts_errors_payload(tmp_path: Path, monkeypatch):
    from core.tools import routes

    creator = make_creator(tmp_path)
    creator.ensure_tools_for_request(LOG_REQUEST)
    monkeypatch.setattr(routes, "get_tool_registry", lambda: creator.registry)
    monkeypatch.setattr(routes, "get_tool_runtime", lambda: creator.runtime)
    app = FastAPI()
    app.include_router(routes.router)

    async def allow_test_request():
        return None

    app.dependency_overrides[routes.verify_api_key] = allow_test_request

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/tools/neron_log_summary_tool/execute",
            json={
                "payload": {
                    "errors": [
                        "ERROR core failed",
                        "CRITICAL planner timeout",
                    ]
                }
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["error_count"] == 2
    assert data["severity"] == "critical"
    assert set(data["components"]) >= {"core", "planner"}
    assert data["excerpt"]
    assert data["recommendation"]
