from __future__ import annotations

import httpx
import pytest

from core import app as core_app
from core.providers import ensure_default_providers, provider_registry


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_selfmodel_endpoints_are_protected():
    transport = httpx.ASGITransport(app=core_app.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/selfmodel/status")

    assert response.status_code == 401


async def test_selfmodel_exposes_internal_truth_sources(monkeypatch):
    ensure_default_providers()
    monkeypatch.setattr(core_app.settings, "API_KEY", "selfmodel-test-key")
    transport = httpx.ASGITransport(app=core_app.app)
    headers = {"X-Neron-API-Key": "selfmodel-test-key"}
    paths = (
        "status",
        "identity",
        "capabilities",
        "providers",
        "services",
        "agents",
        "memory",
        "goals",
        "architecture",
    )

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=headers,
    ) as client:
        responses = {path: await client.get(f"/selfmodel/{path}") for path in paths}

    assert all(response.status_code == 200 for response in responses.values())
    assert responses["identity"].json()["name"] == "Néron"
    assert "available" in responses["capabilities"].json()
    assert "providers" in responses["providers"].json()
    assert responses["services"].json()["source"] == "service_registry"
    assert {"registry", "a2a"} <= responses["agents"].json().keys()
    assert "provider" in responses["memory"].json()
    assert {"engine", "runtime", "tasks"} <= responses["goals"].json().keys()
    assert responses["architecture"].json()["self_awareness"] == "self_model"


async def test_open_meteo_is_a2a_agent_and_never_a_provider(monkeypatch):
    ensure_default_providers()
    monkeypatch.setattr(core_app.settings, "API_KEY", "selfmodel-test-key")
    transport = httpx.ASGITransport(app=core_app.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Neron-API-Key": "selfmodel-test-key"},
    ) as client:
        providers = (await client.get("/selfmodel/providers")).json()
        agents = (await client.get("/selfmodel/agents")).json()

    assert "open_meteo" not in {item["name"] for item in providers["providers"]}
    provider_names = {item["name"] for item in providers["providers"]}
    agent_ids = {item["agent_id"] for item in agents["agents"]}
    assert "open_meteo" in agent_ids
    assert provider_names.isdisjoint(agent_ids)
    assert all(
        item["kind"] == "provider"
        and item["runtime_type"] == "persistent"
        and item["managed_by"] == "provider_registry"
        for item in providers["providers"]
    )
    assert all(
        item["kind"] == "agent"
        and item["runtime_type"] in {"persistent", "temporary", "unknown"}
        and item["managed_by"] in {"agent_registry", "a2a", "goal", "unknown"}
        for item in agents["agents"]
    )
    open_meteo = next(item for item in agents["agents"] if item["agent_id"] == "open_meteo")
    assert open_meteo["kind"] == "agent"
    assert open_meteo["runtime_type"] == "persistent"
    assert open_meteo["managed_by"] == "a2a"
    assert provider_registry.get("open_meteo") is None


async def test_selfmodel_architecture_documents_strict_separation(monkeypatch):
    monkeypatch.setattr(core_app.settings, "API_KEY", "selfmodel-test-key")
    transport = httpx.ASGITransport(app=core_app.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Neron-API-Key": "selfmodel-test-key"},
    ) as client:
        architecture = (await client.get("/selfmodel/architecture")).json()

    assert architecture["separation"]["providers"]["kind"] == "provider"
    assert architecture["separation"]["agents"]["kind"] == "agent"
    assert architecture["separation"]["agents"]["developed_by"] == "goal_engine"
    assert architecture["separation"]["agents"]["future_manager"] == "provider_agent"


async def test_existing_status_route_remains_available(monkeypatch):
    monkeypatch.setattr(core_app.settings, "API_KEY", "selfmodel-test-key")
    transport = httpx.ASGITransport(app=core_app.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": "selfmodel-test-key"},
    ) as client:
        response = await client.get("/status")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
