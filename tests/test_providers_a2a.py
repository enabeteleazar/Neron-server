from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from core import app as core_app
from core.a2a import A2AClient, AgentCard, AgentMessage, AgentTask
from core.providers import ensure_default_providers, provider_registry
from core.providers.llm import LLMProvider
from core.providers.memory import ObliviaProvider
from core.providers.models import ProviderRequest
from core.providers.registry import ProviderRegistry


API_KEY = "providers-a2a-test-key"
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def configure_auth(monkeypatch):
    monkeypatch.setattr(core_app.settings, "API_KEY", API_KEY)
    yield


class FakeProvider:
    name = "fake"
    type = "generic"
    status = "healthy"
    capabilities = ["health", "execute"]

    async def health(self):
        return {"status": "healthy"}

    async def execute(self, request):
        return {"status": "healthy", "request": request}


class FakeLLMClient:
    async def health(self):
        return {"status": "ok", "provider": "fake-llm"}

    async def generate(self, task_type, prompt, context, request_id=None):
        class Result:
            result = f"generated:{prompt}"
            model_used = "fake-model"
            latency_ms = 12
            warning = None

        return Result()


def test_provider_registry_registers_lists_gets_and_filters():
    registry = ProviderRegistry()

    info = registry.register(FakeProvider())

    assert info.name == "fake"
    assert registry.get("fake") is not None
    assert [provider.name for provider in registry.list()] == ["fake"]
    assert [provider.name for provider in registry.by_type("generic")] == ["fake"]
    assert registry.capabilities() == ["execute", "health"]
    assert registry.status()["count"] == 1


async def test_oblivia_provider_health_remember_recall_search_status(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "memory.oblivia.semantic.vector_index.LocalEmbedder",
        lambda: type("Embedder", (), {"embed": lambda self, text: [0.0, 1.0]})(),
    )
    db_path = tmp_path / "memory.db"
    vault_path = tmp_path / "obsidian"

    from memory.oblivia import ObliviaMemoryManager

    provider = ObliviaProvider(
        ObliviaMemoryManager(
            sqlite_path=str(db_path),
            obsidian_path=str(vault_path),
        )
    )

    health = await provider.health()
    remembered = await provider.execute(
        ProviderRequest(
            action="remember",
            payload={
                "content": "Néron utilise Oblivia comme mémoire provider.",
                "category": "project",
            },
            trace_id="trace-memory",
        )
    )
    recalled = await provider.execute(
        ProviderRequest(action="recall", payload={"query": "Oblivia", "limit": 5})
    )
    searched = await provider.execute(
        ProviderRequest(action="search", payload={"query": "provider", "limit": 5})
    )
    status = await provider.execute(ProviderRequest(action="status"))

    assert health.status == "healthy"
    assert remembered.status == "healthy"
    assert remembered.trace_id == "trace-memory"
    assert recalled.result
    assert searched.result
    assert status.result["ok"] is True
    assert Path(status.result["sqlite"]["path"]) == db_path


async def test_llm_provider_health_generate_and_status():
    provider = LLMProvider(client=FakeLLMClient())

    health = await provider.health()
    generated = await provider.execute(
        ProviderRequest(
            action="generate",
            payload={"prompt": "Bonjour", "task_type": "chat"},
            trace_id="trace-llm",
        )
    )
    status = await provider.execute(ProviderRequest(action="status"))

    assert health.status == "healthy"
    assert generated.status == "healthy"
    assert generated.result["text"] == "generated:Bonjour"
    assert generated.result["model"] == "fake-model"
    assert generated.trace_id == "trace-llm"
    assert status.result["provider"] == "fake-llm"


async def test_a2a_client_health_and_send_task():
    client = A2AClient(
        [
            AgentCard(
                agent_id="agent-1",
                name="Agent One",
                capabilities=["analysis"],
                status="available",
            )
        ]
    )

    health = await client.health()
    response = await client.send_task(
        AgentTask(
            target_agent="agent-1",
            messages=[AgentMessage(content="Analyse ce signal.")],
            trace_id="trace-a2a",
        )
    )
    missing = await client.send_task(AgentTask(target_agent="missing"))

    assert health["status"] == "available"
    assert health["mode"] == "local_mock"
    assert response.status == "accepted"
    assert response.trace_id == "trace-a2a"
    assert missing.status == "failed"
    assert missing.error == "agent not found"


def test_default_providers_are_registered_idempotently():
    registry = ProviderRegistry()

    ensure_default_providers(registry)
    ensure_default_providers(registry)

    payload = registry.status()
    assert payload["count"] == 2
    assert {provider["name"] for provider in payload["providers"]} == {
        "oblivia",
        "llm",
    }
    assert "memory" in payload["types"]
    assert "llm" in payload["types"]


async def test_status_exposes_providers_and_a2a():
    provider_registry.clear()
    transport = httpx.ASGITransport(app=core_app.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {A}"PI_KEY},
    ) as client:
        response = await client.get("/status")

    assert response.status_code == 200
    payload = response.json()
    providers = payload["providers"]["providers"]
    assert {provider["name"] for provider in providers} >= {"oblivia", "llm"}
    assert payload["providers"]["types"]["memory"] >= 1
    assert payload["providers"]["types"]["llm"] >= 1
    assert payload["providers"]["memory_provider"]["name"] == "oblivia"
    assert payload["providers"]["llm_provider"]["name"] == "llm"
    assert "health" in payload["providers"]["capabilities"]
    assert payload["a2a"]["available"] is True
    assert payload["a2a"]["mode"] == "local_mock"
