from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from core.agent_factory.registry import DynamicAgentRegistry
from core.agent_runtime.runtime import (
    AgentNotFoundError,
    AgentRuntime,
)
from core.agent_runtime.store import AgentRuntimeStore
from core.capabilities.models import CapabilityRequest
from core.capabilities.registry import CapabilityRegistry
from core.capabilities.resolver import CapabilityResolver
from core.tools.creator import ToolCreator
from core.tools.models import ToolSpec
from core.tools.registry import ToolRegistry
from core.tools.runtime import ToolRuntime


pytestmark = pytest.mark.asyncio


class EmptyProjectManager:
    def list_projects(self, status=None, limit=100):
        return []


def write_agent(
    directory: Path,
    slug: str,
    *,
    body: str,
    spec: dict | None = None,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload = spec or {
        "kind": "agent",
        "name": slug,
        "goal": f"Exécuter {slug}",
        "capabilities": ["test"],
    }
    (directory / f"{slug}.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                f"AGENT_SPEC = {json.dumps(payload, ensure_ascii=False)}",
                "class Agent:",
                f"    name = {slug!r}",
                body,
                "",
            ]
        ),
        encoding="utf-8",
    )


def make_runtime(
    tmp_path: Path,
    *,
    tool_registry: ToolRegistry | None = None,
    tool_runtime: ToolRuntime | None = None,
) -> tuple[AgentRuntime, Path]:
    generated = tmp_path / "generated"
    runtime = AgentRuntime(
        registry=DynamicAgentRegistry(generated),
        tool_registry=tool_registry or ToolRegistry(tmp_path / "tools.json"),
        tool_runtime=tool_runtime,
        store=AgentRuntimeStore(tmp_path / "runtime.sqlite3"),
    )
    return runtime, generated


async def test_load_existing_agent_and_reject_missing(tmp_path: Path):
    runtime, generated = make_runtime(tmp_path)
    write_agent(
        generated,
        "echo_agent",
        body=(
            "    async def execute(self, text=''):\n"
            "        return {'status': 'ok', 'response': text}"
        ),
    )

    instance = runtime.load_agent("echo_agent")

    assert instance.agent_slug == "echo_agent"
    assert instance.spec["name"] == "echo_agent"
    with pytest.raises(AgentNotFoundError, match="agent_not_found"):
        runtime.load_agent("absent_agent")


async def test_run_agent_injects_context_and_persists_success(tmp_path: Path):
    runtime, generated = make_runtime(tmp_path)
    write_agent(
        generated,
        "context_agent",
        body=(
            "    async def execute(self, request='', context=None, metadata=None):\n"
            "        return {\n"
            "            'status': 'ok',\n"
            "            'response': f\"{request}:{context.context['scope']}:{metadata['source']}\",\n"
            "        }"
        ),
    )

    result = await runtime.run_agent(
        "context_agent",
        "analyse",
        context={"scope": "core"},
        metadata={"source": "test"},
    )
    stored = runtime.store.get_execution(result.execution_id)

    assert result.ok is True
    assert result.response == "analyse:core:test"
    assert stored is not None
    assert stored["status"] == "completed"
    assert stored["response"] == result.response
    assert stored["duration_ms"] is not None


async def test_run_agent_records_failure(tmp_path: Path):
    runtime, generated = make_runtime(tmp_path)
    write_agent(
        generated,
        "broken_agent",
        body=(
            "    async def execute(self, text=''):\n"
            "        raise RuntimeError('agent exploded')"
        ),
    )

    result = await runtime.run_agent("broken_agent", "test")

    assert result.ok is False
    assert result.status == "failed"
    assert result.error == "agent exploded"
    assert runtime.store.get_execution(result.execution_id)["status"] == "failed"


async def test_tool_binding_is_injected_and_uses_tool_runtime(tmp_path: Path):
    registry = ToolRegistry(tmp_path / "tools.json")
    registry.register_tool(
        ToolSpec(
            name="Upper",
            slug="upper_tool",
            description="Uppercase text",
        )
    )
    tool_runtime = ToolRuntime(
        registry,
        handlers={
            "upper_tool": lambda payload: {
                "ok": True,
                "response": str(payload["value"]).upper(),
                "data": {"value": str(payload["value"]).upper()},
            }
        },
    )
    runtime, generated = make_runtime(
        tmp_path,
        tool_registry=registry,
        tool_runtime=tool_runtime,
    )
    write_agent(
        generated,
        "tool_agent",
        spec={
            "kind": "agent",
            "name": "tool_agent",
            "goal": "Use upper tool",
            "tools": ["upper_tool"],
        },
        body=(
            "    async def execute(self, text='', tools=None):\n"
            "        result = await tools['upper_tool'].execute({'value': text})\n"
            "        return {'status': 'ok', 'response': result.response}"
        ),
    )

    result = await runtime.run_agent("tool_agent", "neron")

    assert result.ok is True
    assert result.response == "NERON"
    assert sorted(runtime.load_agent("tool_agent").tools) == ["upper_tool"]


async def test_missing_declared_tool_fails_before_execution(tmp_path: Path):
    runtime, generated = make_runtime(tmp_path)
    write_agent(
        generated,
        "missing_tool_agent",
        spec={
            "kind": "agent",
            "name": "missing_tool_agent",
            "goal": "Use missing tool",
            "required_tools": ["absent_tool"],
        },
        body=(
            "    async def execute(self, text=''):\n"
            "        return {'status': 'ok', 'response': 'should not run'}"
        ),
    )

    result = await runtime.run_agent("missing_tool_agent", "test")

    assert result.ok is False
    assert result.error == "agent_tool_unavailable:absent_tool"


async def test_runtime_api_status_history_and_run(monkeypatch, tmp_path: Path):
    from core.agent_runtime import routes

    runtime, generated = make_runtime(tmp_path)
    write_agent(
        generated,
        "api_agent",
        body=(
            "    async def execute(self, text=''):\n"
            "        return {'status': 'ok', 'response': f'API {text}'}"
        ),
    )
    monkeypatch.setattr(routes, "get_agent_runtime", lambda: runtime)
    app = FastAPI()
    app.include_router(routes.router)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": "test-api-key"},
    ) as client:
        response = await client.post(
            "/agents/runtime/run/api_agent",
            json={"request": "ok"},
        )
        execution_id = response.json()["execution_id"]
        status = await client.get("/agents/runtime/status")
        executions = await client.get("/agents/runtime/executions")
        detail = await client.get(
            f"/agents/runtime/executions/{execution_id}"
        )

    assert response.status_code == 200
    assert response.json()["response"] == "API ok"
    assert status.json()["loaded_agents_count"] == 1
    assert status.json()["execution_count"] == 1
    assert executions.json()["count"] == 1
    assert detail.json()["execution_id"] == execution_id


async def test_capability_resolver_runs_log_agent_through_tool_runtime(
    tmp_path: Path,
):
    tool_registry = ToolRegistry(tmp_path / "tools.json")
    tool_runtime = ToolRuntime(
        tool_registry,
        log_provider=lambda payload: [
            "INFO ready",
            "ERROR core failed",
            "CRITICAL planner timeout",
        ],
    )
    ToolCreator(tool_registry, tool_runtime).ensure_tools_for_request(
        "Analyse les logs Néron"
    )
    runtime, generated = make_runtime(
        tmp_path,
        tool_registry=tool_registry,
        tool_runtime=tool_runtime,
    )
    write_agent(
        generated,
        "logs_agent",
        spec={
            "kind": "agent",
            "name": "logs_agent",
            "goal": (
                "Analyse automatiquement les logs Néron "
                "et résume les erreurs critiques"
            ),
            "tools": [
                "neron_log_reader_tool",
                "neron_log_error_filter_tool",
                "neron_log_summary_tool",
            ],
        },
        body=(
            "    async def execute(self, tools=None, context=None):\n"
            "        read = await tools['neron_log_reader_tool'].execute({})\n"
            "        filtered = await tools['neron_log_error_filter_tool'].execute(read.data)\n"
            "        summary = await tools['neron_log_summary_tool'].execute(filtered.data)\n"
            "        return {'status': 'ok', 'response': summary.response, **summary.data}"
        ),
    )
    resolver = CapabilityResolver(
        registry=CapabilityRegistry(
            agent_registry=runtime.registry,
            project_manager=EmptyProjectManager(),
            builtins=[],
        ),
        runtime_manager=runtime,
    )

    result = await resolver.resolve(
        CapabilityRequest(text="Analyse les logs Néron")
    )

    assert result is not None
    assert result.decision is not None
    assert result.decision.decision == "use_existing_agent"
    assert result.agent_slug == "logs_agent"
    assert "2 erreur" in result.response
    assert runtime.store.count_executions() == 1
