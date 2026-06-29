from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from core import app as core_app
from core.infrastructure.event_bus import Event, EventBus, event_bus
from core.infrastructure.gateway import (
    Gateway,
    GatewayTimeoutError,
    ServiceNotRegisteredError,
    ServiceUnavailableError,
)
from core.infrastructure.logging import log_event
from core.infrastructure.registry import (
    ServiceRegistration,
    ServiceRegistry,
    service_registry,
)


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
                "status": "healthy",
                "capabilities": ["jobs.execute"],
                "metadata": {"zone": "local"},
            },
        )
        listed = await client.get("/registry/services")
        heartbeat = await client.post(
            "/registry/heartbeat",
            json={"service_name": "worker"},
        )

    assert registered.status_code == 200
    assert registered.json()["status"] == "healthy"
    assert listed.status_code == 200
    assert listed.json()["services"][0]["service_name"] == "worker"
    assert listed.json()["services"][0]["status"] == "healthy"
    assert heartbeat.status_code == 200
    assert heartbeat.json()["status"] == "healthy"
    assert heartbeat.json()["last_seen"] >= registered.json()["last_seen"]
    assert heartbeat.json()["last_heartbeat"] >= registered.json()["last_heartbeat"]


async def test_registry_heartbeat_updates_status_without_legacy_mapping():
    async with _client() as client:
        registered = await client.post(
            "/registry/register",
            json={
                "service_name": "status-worker",
                "host": "127.0.0.1",
                "port": 8020,
                "status": "healthy",
            },
        )
        heartbeat = await client.post(
            "/registry/heartbeat",
            json={
                "service_name": "status-worker",
                "status": "degraded",
            },
        )
        healthy = await client.get(
            "/registry/services",
            params={"status": "healthy"},
        )
        degraded = await client.get(
            "/registry/services",
            params={"status": "degraded"},
        )

    assert registered.json()["status"] == "healthy"
    assert heartbeat.json()["status"] == "degraded"
    assert healthy.json()["count"] == 0
    assert degraded.json()["services"][0]["status"] == "degraded"


def test_service_registration_is_strict():
    service = ServiceRegistration(
        service_name="worker",
        host="127.0.0.1",
        port=8020,
        status="healthy",
        capabilities=["jobs.execute"],
        metadata={"zone": "local"},
    )
    assert service.status == "healthy"
    assert service.registered_at.tzinfo == timezone.utc
    assert service.last_seen.tzinfo == timezone.utc

    invalid_services = (
        {"service_name": "", "host": "localhost", "port": 1},
        {"service_name": "worker", "host": "", "port": 1},
        {"service_name": "worker", "host": "localhost", "port": 0},
        {
            "service_name": "worker",
            "host": "localhost",
            "port": 1,
            "status": "online",
        },
        {
            "service_name": "worker",
            "host": "localhost",
            "port": 1,
            "capabilities": [1],
        },
    )
    for invalid in invalid_services:
        with pytest.raises(ValidationError):
            ServiceRegistration(**invalid)


def test_registry_filters_by_status_and_capability():
    registry = ServiceRegistry()
    registry.register(
        ServiceRegistration(
            service_name="worker-a",
            host="127.0.0.1",
            port=8021,
            status="healthy",
            capabilities=["jobs.execute", "metrics.read"],
        )
    )
    registry.register(
        ServiceRegistration(
            service_name="worker-b",
            host="127.0.0.1",
            port=8022,
            status="degraded",
            capabilities=["metrics.read"],
        )
    )

    assert [
        service["service_name"]
        for service in registry.list_services(status="healthy")
    ] == ["worker-a"]
    assert len(registry.list_services(capability="metrics.read")) == 2
    assert [
        service["service_name"]
        for service in registry.list_services(capability="jobs.execute")
    ] == ["worker-a"]


def test_registry_unregister_and_get_service():
    registry = ServiceRegistry()
    registry.register(
        service_name="worker",
        host="127.0.0.1",
        port=8020,
    )

    assert registry.get_service("worker")["service_name"] == "worker"
    assert registry.unregister("worker")["service_name"] == "worker"
    assert registry.get_service("worker") is None
    assert registry.unregister("worker") is None


def test_registry_marks_stale_services():
    registry = ServiceRegistry()
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    registry.register(
        ServiceRegistration(
            service_name="stale-worker",
            host="127.0.0.1",
            port=8020,
            status="healthy",
            registered_at=stale_time,
            last_seen=stale_time,
        )
    )

    stale = registry.mark_stale_services(timeout_seconds=60)

    assert len(stale) == 1
    assert stale[0]["service_name"] == "stale-worker"
    assert stale[0]["status"] == "unhealthy"
    assert registry.mark_stale_services(timeout_seconds=60) == []


def test_registry_operations_publish_events():
    bus = EventBus(test_mode=True)
    registry = ServiceRegistry(bus)
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    registry.register(
        ServiceRegistration(
            service_name="worker",
            host="127.0.0.1",
            port=8020,
            status="healthy",
            registered_at=stale_time,
            last_seen=stale_time,
        )
    )
    registry.heartbeat("worker", status="degraded", metadata={"load": "high"})
    registry.mark_stale_services(timeout_seconds=0)
    registry.unregister("worker")

    events = bus.get_events()
    assert [event["type"] for event in events] == [
        "registry.service_registered",
        "registry.service_heartbeat",
        "registry.service_stale",
        "registry.service_unregistered",
    ]
    assert all(event["source"] == "core.service_registry" for event in events)
    assert all(event["target"] == "worker" for event in events)
    assert events[2]["level"] == "warning"


async def test_registry_routes_get_filter_and_unregister():
    async with _client() as client:
        registered = await client.post(
            "/registry/register",
            json={
                "service_name": "route-worker",
                "host": "127.0.0.1",
                "port": 8020,
                "status": "healthy",
                "capabilities": ["jobs.execute"],
            },
        )
        fetched = await client.get("/registry/services/route-worker")
        filtered = await client.get(
            "/registry/services",
            params={"status": "healthy", "capability": "jobs.execute"},
        )
        removed = await client.delete("/registry/services/route-worker")
        missing = await client.get("/registry/services/route-worker")

    assert registered.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["service_name"] == "route-worker"
    assert filtered.status_code == 200
    assert filtered.json()["count"] == 1
    assert removed.status_code == 200
    assert missing.status_code == 404


async def test_registry_route_rejects_invalid_service():
    async with _client() as client:
        response = await client.post(
            "/registry/register",
            json={"service_name": "", "host": "", "port": 0},
        )

    assert response.status_code == 422


def _gateway_registry(status: str = "healthy") -> ServiceRegistry:
    registry = ServiceRegistry()
    registry.register(
        ServiceRegistration(
            service_name="doctor",
            host="127.0.0.1",
            port=8020,
            status=status,
        )
    )
    return registry


def test_gateway_refuses_absent_and_unhealthy_services():
    bus = EventBus(test_mode=True)
    gateway = Gateway(ServiceRegistry(), bus)
    with pytest.raises(ServiceNotRegisteredError):
        gateway.resolve_service("missing")

    gateway = Gateway(_gateway_registry("unhealthy"), bus)
    with pytest.raises(ServiceUnavailableError):
        gateway.resolve_service("doctor")

    gateway = Gateway(_gateway_registry("unknown"), bus)
    with pytest.raises(ServiceUnavailableError):
        gateway.resolve_service("doctor")


def test_gateway_accepts_healthy_and_degraded_services():
    bus = EventBus(test_mode=True)

    assert Gateway(
        _gateway_registry("healthy"),
        bus,
    ).resolve_service("doctor")["status"] == "healthy"
    assert Gateway(
        _gateway_registry("degraded"),
        bus,
    ).resolve_service("doctor")["status"] == "degraded"


async def test_gateway_proxies_get_with_safe_headers_and_trace_id():
    captured = {}

    async def upstream(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(
            200,
            json={"status": "healthy"},
            headers={"X-Upstream-Secret": "hidden"},
        )

    bus = EventBus(test_mode=True)
    gateway = Gateway(
        _gateway_registry(),
        bus,
        transport=httpx.MockTransport(upstream),
    )
    response = await gateway.proxy_request(
        "doctor",
        "health",
        "GET",
        headers={
            "X-API-Key": "core-secret",
            "Authorization": "Bearer secret",
            "X-Neron-API-Key": "internal-key",
            "X-Neron-Trace-Id": "trace-gateway",
        },
        query_params=[("full", "true")],
    )

    request = captured["request"]
    assert str(request.url) == "http://127.0.0.1:8020/health?full=true"
    assert "x-api-key" not in request.headers
    assert "authorization" not in request.headers
    assert request.headers["x-neron-api-key"] == "internal-key"
    assert request.headers["x-neron-trace-id"] == "trace-gateway"
    assert response.status_code == 200
    assert response.trace_id == "trace-gateway"
    assert "x-upstream-secret" not in response.headers

    events = bus.get_events()
    assert [event["type"] for event in events] == [
        "gateway.request",
        "gateway.response",
    ]
    assert all(event["trace_id"] == "trace-gateway" for event in events)


async def test_gateway_timeout_returns_clean_error_and_event():
    async def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("upstream timeout", request=request)

    bus = EventBus(test_mode=True)
    gateway = Gateway(
        _gateway_registry(),
        bus,
        timeout_seconds=0.1,
        transport=httpx.MockTransport(timeout),
    )

    with pytest.raises(GatewayTimeoutError) as captured:
        await gateway.proxy_request("doctor", "health", "GET")

    assert captured.value.status_code == 504
    events = bus.get_events()
    assert [event["type"] for event in events] == [
        "gateway.request",
        "gateway.error",
    ]
    assert events[-1]["level"] == "error"
    assert events[-1]["payload"]["status_code"] == 504


async def test_gateway_route_maps_registry_errors():
    async with _client() as client:
        missing = await client.get("/gateway/missing/health")
        await client.post(
            "/registry/register",
            json={
                "service_name": "doctor",
                "host": "127.0.0.1",
                "port": 8020,
                "status": "unhealthy",
            },
        )
        unhealthy = await client.get("/gateway/doctor/health")

    assert missing.status_code == 404
    assert unhealthy.status_code == 503


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
