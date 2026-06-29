from __future__ import annotations

from pathlib import Path
import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from memory import app as memory_app


@pytest.fixture
def memory_service(tmp_path: Path):
    return memory_app.MemoryService(
        tmp_path / "memory.db",
        tmp_path / "obsidian",
    )


@pytest.fixture
def configure_app(memory_service):
    memory_app.app.state.memory_service = memory_service
    memory_app.app.state.started_at = time.monotonic()
    return memory_service


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=memory_app.app),
        base_url="http://memory.test",
    )


@pytest.mark.asyncio
async def test_health_and_status(configure_app):
    async with _client() as client:
        health = await client.get("/health")
        status = await client.get("/status")

    assert health.json() == {"service": "memory", "status": "healthy"}
    assert status.status_code == 200
    assert status.json()["service"] == "memory"
    assert status.json()["status"] == "running"
    assert status.json()["backends"]["sqlite"]["records"] == 0


@pytest.mark.asyncio
async def test_remember_recall_and_search(configure_app):
    async with _client() as client:
        remembered = await client.post(
            "/memory/remember",
            json={
                "content": "Néron utilise une mémoire SQLite",
                "category": "lesson",
                "metadata": {"source": "pytest"},
            },
        )
        recalled = await client.post(
            "/memory/recall",
            json={"query": "mémoire sqlite", "limit": 10},
        )
        searched = await client.get(
            "/memory/search",
            params={"q": "mémoire sqlite"},
        )

    assert remembered.status_code == 200
    assert remembered.json()["memory"]["category"] == "lesson"
    assert recalled.json()["count"] >= 1
    assert recalled.json()["results"][0]["backend"] == "sqlite"
    assert searched.json()["count"] >= 1


@pytest.mark.asyncio
async def test_memory_routes_reject_invalid_payload(configure_app):
    async with _client() as client:
        blank = await client.post(
            "/memory/remember",
            json={"content": "   "},
        )
        invalid_limit = await client.post(
            "/memory/recall",
            json={"query": "test", "limit": 0},
        )

    assert blank.status_code == 422
    assert invalid_limit.status_code == 422


def test_memory_registry_payload_uses_common_sdk():
    with patch.object(memory_app, "RegistryClient") as client_class:
        client = memory_app.create_registry_client()

    assert client is client_class.return_value
    client_class.assert_called_once_with(
        service_name="memory",
        version="0.1.0",
        host="localhost",
        port=8040,
        capabilities=["memory", "sqlite", "obsidian", "context_storage"],
        metadata={},
    )


@pytest.mark.asyncio
async def test_memory_lifespan_starts_and_stops_registry(memory_service):
    registry = Mock()
    registry.start = AsyncMock()
    registry.stop = AsyncMock()

    with (
        patch.object(
            memory_app,
            "create_memory_service",
            return_value=memory_service,
        ),
        patch.object(
            memory_app,
            "create_registry_client",
            return_value=registry,
        ),
    ):
        async with memory_app.lifespan(memory_app.app):
            registry.start.assert_awaited_once()
            assert memory_app.app.state.memory_service is memory_service

    registry.stop.assert_awaited_once()
