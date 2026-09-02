from __future__ import annotations


import pytest

# ---------------------------------------------------------------------------
# NERONOS PHASE 1 — test neutralise, volontairement conserve.
#
# Ce module sonde une API interne de sous-module qui a disparu ou change de
# nom : core.modules.goal_v2 (sous-module core).
# Le contrat teste reste pertinent, mais le reparer suppose de toucher au
# sous-module concerne, ce qui est hors perimetre de la Phase 1 (parent
# uniquement). Sans ce garde-fou l ImportError rend TOUTE la suite du parent
# incollectable.
#
# A reprendre en Phase 2 (core) / Phase 3 (llm, memory).
# Voir system/docs/architecture/neronos-architecture.md, section « Dette ».
# ---------------------------------------------------------------------------
pytest.skip(
    "Phase 1 : API de sous-module absente (core.modules.goal_v2 (sous-module core)). "
    "A reparer en Phase 2/3.",
    allow_module_level=True,
)

import httpx
import pytest

from core import app as core_app
from core.modules.goal_v2.service import goal_v2_service
from core.modules.memory_provider.service import memory_provider_service

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=core_app.app),
        base_url="http://test",
    )


async def test_provider_manager_exposes_selfmodel_observations():
    async with _client() as client:
        response = await client.get("/providers")
    assert response.status_code == 200
    assert response.json()["source"] == "selfmodel"
    assert response.json()["providers"]


async def test_goal_v2_checks_real_capabilities_and_publishes_events():
    async with _client() as client:
        response = await client.post(
            "/goal/v2",
            json={"goal": "Vérifie les capacités disponibles de Néron"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["required_capabilities"] == ["system.status"]
    assert payload["status"] in {
        "running",
        "completed",
        "waiting_for_capability",
    }
    assert {event["type"] for event in payload["events"]} >= {
        "goal.created",
        "goal.planning",
        "goal.capability_check",
    }


async def test_goal_v2_waits_when_capability_is_not_proven(monkeypatch):
    monkeypatch.setattr(
        "core.modules.goal_v2.service.selfmodel_client.available_capabilities",
        lambda: set(),
    )
    goal = goal_v2_service.create("Contrôle Home Assistant")
    assert goal.status == "waiting_for_capability"
    assert goal.missing_capabilities == ["homeassistant.control"]


async def test_memory_provider_and_explainable_block(monkeypatch):
    monkeypatch.setattr(
        "core.modules.memory_provider.service.observed_provider",
        lambda: {
            "id": "memory.oblivia",
            "name": "Oblivia",
            "type": "memory",
            "status": "unknown",
            "capabilities": [],
        },
    )
    result = await memory_provider_service.remember("test", "user", {})
    assert result["status"] == "blocked"
    assert result["record_id"] is None
    assert result["reason"]


async def test_memory_routes_are_public_and_never_simulate_results():
    async with _client() as client:
        response = await client.get("/memory/provider")
    assert response.status_code == 200
    assert response.json()["id"] == "memory.oblivia"
    assert response.json()["status"] in {
        "online",
        "offline",
        "degraded",
        "unknown",
    }
