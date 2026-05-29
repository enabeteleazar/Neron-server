import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class DummyAgent:
    def __init__(self, ok=True):
        self.ok = ok

    async def check_connection(self):
        return self.ok


def test_existing_health_endpoint_stays_compatible():
    TestClient = pytest.importorskip("fastapi.testclient").TestClient
    from app import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "version" in response.json()


def test_health_center_status_endpoint_shape(tmp_path, monkeypatch):
    TestClient = pytest.importorskip("fastapi.testclient").TestClient
    monkeypatch.setenv("NERON_EVENTS_JSONL", str(tmp_path / "events.jsonl"))
    from core.health.events import HealthEventBus
    from core.health.snapshot import health_center
    from app import app

    health_center.event_bus = HealthEventBus(tmp_path / "events.jsonl")
    health_center.configure({})

    client = TestClient(app)
    response = client.get("/health-center/status")

    assert response.status_code == 200
    data = response.json()
    assert set(["status", "services", "resources", "diagnostics", "recommendations", "events", "timestamp"]).issubset(data)
    assert data["status"] in {"stable", "degraded", "critical"}


def test_health_snapshot_generation_and_event_publication(tmp_path):
    from core.health.events import HealthEventBus
    from core.health.snapshot import HealthCenter

    events_path = tmp_path / "events.jsonl"
    center = HealthCenter(event_bus=HealthEventBus(events_path))
    center.configure({"llm": DummyAgent(True), "stt": DummyAgent(True), "tts": DummyAgent(True)})

    snapshot = asyncio.run(center.create_snapshot())

    assert snapshot["status"] in {"stable", "degraded", "critical"}
    assert "cpu_pct" in snapshot["resources"]
    assert snapshot["services"]["llm"]["status"] == "ok"
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    assert any(event["type"] == "health.snapshot.created" for event in events)


def test_diagnostics_and_recommendations_for_unreachable_service():
    from core.health.diagnostics import build_diagnostics, build_recommendations, status_from_diagnostics

    snapshot = {
        "resources": {"cpu_pct": 10, "ram_pct": 20, "disk_pct": 30},
        "services": {"llm": {"status": "unreachable", "critical": True, "detail": "timeout"}},
    }

    diagnostics = build_diagnostics(snapshot, [])
    recommendations = build_recommendations(diagnostics)

    assert status_from_diagnostics(diagnostics) == "critical"
    assert diagnostics[0]["code"] == "service.unreachable"
    assert recommendations


def test_self_model_consumes_health_center(monkeypatch):
    from core import self_model

    async def fake_snapshot():
        return {
            "status": "stable",
            "services": {},
            "resources": {"cpu_pct": 1},
            "diagnostics": [],
            "timestamp": "2026-05-29T00:00:00+00:00",
        }

    monkeypatch.setattr(self_model.health_center, "create_snapshot", fake_snapshot)
    state = asyncio.run(self_model.get_self_state())

    assert state["identity"] == "neron"
    assert state["status"] == "stable"
    assert state["internal_health"]["resources"]["cpu_pct"] == 1


def test_world_model_consumes_health_center(monkeypatch):
    from core import world_model

    async def fake_snapshot():
        return {
            "status": "degraded",
            "resources": {"disk_pct": 91},
            "events": [{"type": "system.service.error"}],
            "recommendations": [],
            "timestamp": "2026-05-29T00:00:00+00:00",
        }

    monkeypatch.setattr(world_model.health_center, "create_snapshot", fake_snapshot)
    state = asyncio.run(world_model.get_environment_state())

    assert state["environment"] == "runtime"
    assert state["status"] == "degraded"
    assert state["health_center"]["events"][0]["type"] == "system.service.error"
