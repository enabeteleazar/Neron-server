from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from core import app as core_app
from core.infrastructure.event_bus import Event, EventBus, event_bus
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
        headers={"Authorization": f"Bearer {A}"PI_KEY},
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
        listed = await client.get(
            "/events",
            params={"event_type": "test.created"},
        )

    assert published.status_code == 200
    event = published.json()
    assert event["type"] == "test.created"
    assert event["trace_id"] == "trace-1"
    assert event["level"] == "info"
    assert UUID(event["event_id"])
    assert datetime.fromisoformat(event["timestamp"]).tzinfo == timezone.utc
    assert listed.status_code == 200
    assert listed.json()["events"] == [event]


def test_event_model_is_strict_and_requires_contract_fields():
    with pytest.raises(ValidationError):
        Event(source="pytest", type="test.invalid", payload=[])
    with pytest.raises(ValidationError):
        Event(source="", type="test.invalid", payload={})
    with pytest.raises(ValidationError):
        Event(source="pytest", type="", payload={})
    with pytest.raises(ValidationError):
        Event(
            source="pytest",
            type="test.invalid",
            payload={},
            level="debug",
        )
    with pytest.raises(ValidationError):
        Event(
            source="pytest",
            type="test.invalid",
            payload={},
            unexpected=True,
        )


def test_event_model_generates_ids_and_utc_timestamp():
    event = Event(source="pytest", type="test.created", payload={"value": 1})

    assert isinstance(event.event_id, UUID)
    assert UUID(event.trace_id)
    assert event.timestamp.tzinfo == timezone.utc
    assert event.level == "info"


def test_event_bus_storage_is_bounded_and_copies_payloads():
    bus = EventBus(max_events=2, test_mode=True)
    payload = {"nested": {"value": 1}}
    bus.publish("test.first", "pytest", payload)
    payload["nested"]["value"] = 99
    bus.publish("test.second", "pytest", {})
    bus.publish("test.third", "pytest", {})

    events = bus.get_events()
    assert [event["type"] for event in events] == ["test.second", "test.third"]
    events[0]["payload"]["mutated"] = True
    assert "mutated" not in bus.get_events()[0]["payload"]


def test_event_bus_filters_and_applies_limit_after_filtering():
    bus = EventBus(max_events=10, test_mode=True)
    bus.publish("task.created", "planner", {}, target="worker", trace_id="trace-a")
    bus.publish("task.completed", "worker", {}, target="planner", trace_id="trace-a")
    bus.publish(
        "task.created",
        "planner",
        {},
        target="worker",
        trace_id="trace-b",
        level="warning",
    )

    assert len(bus.get_events(event_type="task.created")) == 2
    assert len(bus.get_events(source="worker")) == 1
    assert len(bus.get_events(target="planner")) == 1
    assert len(bus.get_events(trace_id="trace-a")) == 2
    assert bus.get_events(1, source="planner")[0]["trace_id"] == "trace-b"
    assert bus.get_events(0) == []


def test_event_bus_rejects_invalid_input_and_limit():
    bus = EventBus(test_mode=True)

    with pytest.raises(ValueError):
        EventBus(max_events=0)
    with pytest.raises(ValueError):
        bus.publish("", "pytest", {})
    with pytest.raises(ValueError):
        bus.publish("test.created", "", {})
    with pytest.raises(TypeError):
        bus.publish("test.created", "pytest", [])
    with pytest.raises(ValidationError):
        bus.publish("test.created", "pytest", {}, level="debug")
    with pytest.raises(ValueError):
        bus.get_events(-1)


def test_event_bus_clear_is_test_only():
    production_bus = EventBus()
    production_bus.publish("test.created", "pytest", {})
    with pytest.raises(RuntimeError, match="test mode"):
        production_bus.clear()

    test_bus = EventBus(test_mode=True)
    test_bus.publish("test.created", "pytest", {})
    test_bus.clear()
    assert test_bus.get_events() == []


async def test_event_routes_support_level_and_filters():
    async with _client() as client:
        await client.post(
            "/events/publish",
            json={
                "event_type": "task.created",
                "source": "planner",
                "target": "worker",
                "payload": {},
                "trace_id": "trace-route",
                "level": "warning",
            },
        )
        await client.post(
            "/events/publish",
            json={
                "event_type": "task.completed",
                "source": "worker",
                "payload": {},
            },
        )
        filtered = await client.get(
            "/events",
            params={
                "event_type": "task.created",
                "source": "planner",
                "target": "worker",
                "trace_id": "trace-route",
            },
        )

    assert filtered.status_code == 200
    assert filtered.json()["count"] == 1
    assert filtered.json()["events"][0]["level"] == "warning"


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
