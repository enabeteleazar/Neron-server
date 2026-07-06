from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from core import app as core_app
from core.infrastructure.event_bus import event_bus
from core.infrastructure.registry import (
    ServiceRegistration,
    ServiceRegistry,
    service_registry,
)
from core.infrastructure.topology import (
    build_topology,
    get_topology_service,
    service_ecosystem_context,
)
from server.common import cli


API_KEY = "topology-test-key"


@pytest.fixture(autouse=True)
def clear_registry(monkeypatch):
    monkeypatch.setattr(core_app.settings, "API_KEY", API_KEY)
    service_registry.clear()
    event_bus.clear()
    yield
    service_registry.clear()
    event_bus.clear()


def _registration(
    name: str,
    status: str = "healthy",
    *,
    last_seen: datetime | None = None,
) -> ServiceRegistration:
    return ServiceRegistration(
        service_name=name,
        host="localhost",
        port=8000,
        version="0.1.0",
        status=status,
        capabilities=["test"],
        metadata={},
        last_seen=last_seen or datetime.now(timezone.utc),
    )


def test_topology_empty_is_unhealthy():
    topology = build_topology(ServiceRegistry())

    assert topology["status"] == "unhealthy"
    assert topology["service_count"] == 0
    assert topology["healthy_count"] == 0
    assert topology["degraded_count"] == 0
    assert topology["offline_count"] == 0
    assert topology["services"] == []


def test_topology_healthy_and_sorted():
    registry = ServiceRegistry()
    registry.register(_registration("web"))
    registry.register(_registration("doctor"))

    topology = build_topology(registry)

    assert topology["status"] == "healthy"
    assert topology["service_count"] == 2
    assert topology["healthy_count"] == 2
    assert [service["name"] for service in topology["services"]] == [
        "doctor",
        "web",
    ]


def test_topology_degraded_and_ecosystem_context():
    registry = ServiceRegistry()
    registry.register(_registration("doctor"))
    registry.register(_registration("llm", "degraded"))

    topology = build_topology(registry)
    context = service_ecosystem_context(registry)

    assert topology["status"] == "degraded"
    assert topology["degraded_count"] == 1
    assert topology["offline_count"] == 0
    assert context["active_services"] == ["doctor", "llm"]
    assert context["unavailable_services"] == []


def test_topology_service_contains_age():
    registry = ServiceRegistry()
    registry.register(
        _registration(
            "goal",
            last_seen=datetime.now(timezone.utc) - timedelta(seconds=4),
        )
    )

    service = get_topology_service(registry, "goal")

    assert service["name"] == "goal"
    assert service["host"] == "localhost"
    assert service["port"] == 8000
    assert service["capabilities"] == ["test"]
    assert service["age_seconds"] >= 4
    assert get_topology_service(registry, "missing") is None


@pytest.mark.asyncio
async def test_topology_routes_are_protected_and_return_service():
    service_registry.register(_registration("goal"))
    transport = httpx.ASGITransport(app=core_app.app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://core.test",
    ) as client:
        protected = await client.get("/registry/topology")
        topology = await client.get(
            "/registry/topology",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        service = await client.get(
            "/registry/topology/goal",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        missing = await client.get(
            "/registry/topology/missing",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

    assert protected.status_code == 401
    assert topology.status_code == 200
    assert topology.json()["service_count"] == 1
    assert service.status_code == 200
    assert service.json()["name"] == "goal"
    assert missing.status_code == 404


def test_cli_registry_and_services(monkeypatch, capsys):
    topology = {
        "status": "healthy",
        "service_count": 2,
        "services": [
            {"name": "doctor", "status": "healthy", "host": "localhost", "port": 8020},
            {"name": "goal", "status": "healthy", "host": "localhost", "port": 8030},
        ],
    }
    calls = []
    monkeypatch.setattr(
        cli,
        "_request",
        lambda path: calls.append(path) or topology,
    )

    assert cli.main(["registry"]) == 0
    registry_output = capsys.readouterr().out
    assert "Néron Registry" in registry_output
    assert "Services : 2" in registry_output
    assert "goal" in registry_output

    assert cli.main(["services"]) == 0
    services_output = capsys.readouterr().out
    assert "Néron Registry" not in services_output
    assert "doctor" in services_output
    assert calls == ["/registry/topology", "/registry/topology"]


def test_cli_service(monkeypatch, capsys):
    service = {
        "name": "goal",
        "status": "healthy",
        "host": "localhost",
        "port": 8030,
        "capabilities": ["planning", "task_loop"],
        "registered_at": "2026-06-29T00:00:00+00:00",
        "last_seen": "2026-06-29T00:00:04+00:00",
        "age_seconds": 2,
    }
    calls = []
    monkeypatch.setattr(
        cli,
        "_request",
        lambda path: calls.append(path) or service,
    )

    assert cli.main(["service", "goal"]) == 0
    output = capsys.readouterr().out
    assert "Nom            : goal" in output
    assert "Capabilities   : planning, task_loop" in output
    assert "Age            : 2s" in output
    assert calls == ["/registry/topology/goal"]
