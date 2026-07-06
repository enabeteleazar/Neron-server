from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from core import app as core_app
from core.api import auth
from core.pipeline.orchestrator import CoreOrchestrator


class ForbiddenAgentRouter:
    async def route(self, *_args, **_kwargs):
        raise AssertionError("A system query must not reach the LLM")


class RegistryFixture:
    def __init__(self) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        self.services = [
            {
                "service_name": "llm",
                "host": "localhost",
                "port": 8765,
                "status": "healthy",
                "capabilities": ["text_generation", "chat", "completion"],
                "registered_at": timestamp,
                "last_seen": timestamp,
            },
            {
                "service_name": "homeassistant",
                "host": "localhost",
                "port": 8123,
                "status": "healthy",
                "capabilities": ["home_automation", "devices"],
                "registered_at": timestamp,
                "last_seen": timestamp,
            },
            {
                "service_name": "memory",
                "host": "localhost",
                "port": 8040,
                "status": "healthy",
                "capabilities": ["memory", "sqlite", "obsidian"],
                "registered_at": timestamp,
                "last_seen": timestamp,
            },
        ]

    def list_services(self):
        return list(self.services)


SYSTEM_QUERIES = [
    ("Qui es-tu ?", "identity_provider", "identity_module"),
    ("Que fais-tu ?", "identity_provider", "identity_module"),
    ("Quelle est ta version ?", "identity_provider", "identity_module"),
    ("Quelle est ton architecture ?", "identity_provider", "identity_module"),
    ("Quels services fonctionnent ?", "status_provider", "status_module"),
    ("Quels services sont enregistrés ?", "registry_provider", "registry_module"),
    ("Quels services sont arrêtés ?", "registry_provider", "registry_module"),
    ("Montre-moi la topologie.", "topology_provider", "topology_module"),
    ("Quel service fournit les LLM ?", "registry_provider", "registry_module"),
    (
        "Quel service gère Home Assistant ?",
        "registry_provider",
        "registry_module",
    ),
    ("Quel service gère la mémoire ?", "registry_provider", "registry_module"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("query", "route", "executor"), SYSTEM_QUERIES)
async def test_system_queries_are_fully_local(
    monkeypatch,
    query: str,
    route: str,
    executor: str,
):
    monkeypatch.setattr(
        "core.pipeline.orchestrator.service_registry",
        RegistryFixture(),
    )
    result = await CoreOrchestrator(
        agent_router=ForbiddenAgentRouter(),
    ).handle(query)

    assert result.decision.selected_route == route
    assert result.decision.requires_llm is False
    assert result.executor == executor
    assert result.model is None
    assert result.error is None


@pytest.mark.asyncio
async def test_input_text_keeps_system_query_out_of_llm(monkeypatch):
    api_key = "system-routing-test-key"
    monkeypatch.setattr(auth.settings, "API_KEY", api_key)
    monkeypatch.setattr(core_app.settings, "API_KEY", api_key)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.service_registry",
        RegistryFixture(),
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())
    monkeypatch.setattr(
        core_app,
        "_active_core_orchestrator",
        lambda: orchestrator,
    )

    transport = httpx.ASGITransport(app=core_app.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/input/text",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"text": "Quel service gère Home Assistant ?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["selected_route"] == "registry_provider"
    assert payload["metadata"]["orchestrator_decision"]["requires_llm"] is False
    assert payload["agent"] == "registry_module"
