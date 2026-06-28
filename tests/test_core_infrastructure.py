from __future__ import annotations

import json
import logging

import httpx
import pytest

from core import app as core_app
from core.infrastructure.event_bus import event_bus
from core.infrastructure.logging import log_event
from core.infrastructure.registry import service_registry


API_KEY = "core-infrastructure-test-key"


@pytest.fixture(autouse=True)
def clear_infrastructure(monkeypatch):
    monkeypatch.setattr(core_app.settings, "API_KEY", API_KEY)
    event_bus.clear()
    service_registry.clear()
    yield
    event_bus.clear()
    service_registry.clear()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=core_app.app),
        base_url="http://testserver",
        headers={"X-API-Key": API_KEY},
    )


async def test_health_uses_unified_contract():
    async with _client() as client:
        response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "core"
    assert payload["status"] == "healthy"
    assert payload["version"]
    assert payload["uptime"] >= 0
    assert payload["started_at"]
    assert payload["timestamp"]


async def test_status_uses_unified_contract():
    async with _client() as client:
        response = await client.get("/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "core"
    assert payload["status"] == "ok"
    assert payload["pid"] > 0
    assert payload["dependencies"] == {}
    assert payload["registry"]["service_count"] == 0
    assert payload["event_bus"]["event_count"] == 0


async def test_publish_and_list_events():
    async with _client() as client:
        published = await client.post(
            "/events/publish",
            json={
                "event_type": "test.created",
                "source": "pytest",
                "target": "core",
                "payload": {"value": 42},
                "trace_id": "trace-1",
            },
        )
        listed = await client.get("/events")

    assert published.status_code == 200
    event = published.json()
    assert event["type"] == "test.created"
    assert event["trace_id"] == "trace-1"
    assert listed.status_code == 200
    assert listed.json()["events"] == [event]


async def test_register_and_heartbeat_service():
    async with _client() as client:
        registered = await client.post(
            "/registry/register",
            json={
                "service_name": "worker",
                "host": "127.0.0.1",
                "port": 8020,
                "version": "1.0.0",
            },
        )
        listed = await client.get("/registry/services")
        heartbeat = await client.post(
            "/registry/heartbeat",
            json={"service_name": "worker"},
        )

    assert registered.status_code == 200
    assert listed.status_code == 200
    assert listed.json()["services"][0]["service_name"] == "worker"
    assert heartbeat.status_code == 200
    assert heartbeat.json()["last_heartbeat"] >= registered.json()["last_heartbeat"]


def test_log_event_emits_json(monkeypatch):
    records = []

    def capture_log(self, level, message, *args, **kwargs):
        if self.name == "neron.core":
            records.append((level, message))

    monkeypatch.setattr(
        logging.Logger,
        "log",
        capture_log,
    )
    log_event(
        "core",
        "info",
        "test_message",
        trace_id="trace-1",
        extra={"value": 42},
    )

    payload = json.loads(records[-1][1])
    assert payload["service"] == "core"
    assert payload["level"] == "INFO"
    assert payload["message"] == "test_message"
    assert payload["trace_id"] == "trace-1"
    assert payload["extra"] == {"value": 42}
