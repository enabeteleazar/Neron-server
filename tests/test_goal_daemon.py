from __future__ import annotations

import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from goal import app as goal_app


@pytest.fixture(autouse=True)
def clear_goal_store():
    goal_app.goal_store.clear()
    goal_app.app.state.started_at = time.monotonic()
    yield
    goal_app.goal_store.clear()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=goal_app.app),
        base_url="http://goal.test",
    )


@pytest.mark.asyncio
async def test_health_and_status():
    async with _client() as client:
        health = await client.get("/health")
        status = await client.get("/status")

    assert health.json() == {"service": "goal", "status": "healthy"}
    assert status.status_code == 200
    assert status.json()["service"] == "goal"
    assert status.json()["status"] == "running"
    assert status.json()["uptime"] >= 0
    assert status.json()["goal_count"] == 0


@pytest.mark.asyncio
async def test_goal_mvp_lifecycle():
    async with _client() as client:
        created = await client.post(
            "/goals",
            json={
                "title": "Tester le daemon",
                "description": "MVP",
                "priority": "high",
            },
        )
        goal = created.json()["goal"]
        listed = await client.get("/goals")
        fetched = await client.get(f"/goals/{goal['id']}")
        cancelled = await client.post(f"/goals/{goal['id']}/cancel")

    assert created.status_code == 202
    assert goal["status"] == "queued"
    assert listed.json()["count"] == 1
    assert fetched.json()["goal"]["id"] == goal["id"]
    assert cancelled.json()["goal"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_goal_routes_reject_invalid_and_missing_goals():
    async with _client() as client:
        invalid = await client.post("/goals", json={"title": "   "})
        missing = await client.get("/goals/missing")
        cancel_missing = await client.post("/goals/missing/cancel")

    assert invalid.status_code == 422
    assert missing.status_code == 404
    assert cancel_missing.status_code == 404


def test_goal_registry_payload_uses_common_sdk():
    with patch.object(goal_app, "RegistryClient") as client_class:
        client = goal_app.create_registry_client()

    assert client is client_class.return_value
    client_class.assert_called_once_with(
        service_name="goal",
        version="0.1.0",
        host="localhost",
        port=8030,
        capabilities=["goal_execution", "planning", "agent_creation", "task_loop"],
        metadata={},
    )


@pytest.mark.asyncio
async def test_goal_lifespan_starts_and_stops_registry():
    registry = Mock()
    registry.start = AsyncMock()
    registry.stop = AsyncMock()

    with patch.object(
        goal_app,
        "create_registry_client",
        return_value=registry,
    ):
        async with goal_app.lifespan(goal_app.app):
            registry.start.assert_awaited_once()
            assert goal_app.app.state.registry_client is registry

    registry.stop.assert_awaited_once()
