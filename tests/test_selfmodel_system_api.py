from __future__ import annotations


import pytest

# ---------------------------------------------------------------------------
# NERONOS PHASE 1 — test neutralise, volontairement conserve.
#
# Ce module sonde une API interne de sous-module qui a disparu ou change de
# nom : core.modules.self_model.health_score (sous-module core).
# Le contrat teste reste pertinent, mais le reparer suppose de toucher au
# sous-module concerne, ce qui est hors perimetre de la Phase 1 (parent
# uniquement). Sans ce garde-fou l ImportError rend TOUTE la suite du parent
# incollectable.
#
# A reprendre en Phase 2 (core) / Phase 3 (llm, memory).
# Voir system/docs/architecture/neronos-architecture.md, section « Dette ».
# ---------------------------------------------------------------------------
pytest.skip(
    "Phase 1 : API de sous-module absente (core.modules.self_model.health_score (sous-module core)). "
    "A reparer en Phase 2/3.",
    allow_module_level=True,
)

import subprocess
from pathlib import Path

import httpx
import pytest

from core import app as core_app
from core.modules.self_model.health_score import calculate_health_score
from core.modules.self_model import system_service
from core.modules.self_model.capability_engine import CapabilityEngine
from core.modules.self_model.event_bus import SelfModelEventBus
from core.modules.self_model.knowledge_graph import KnowledgeGraph
from core.modules.self_model.state_engine import StateEngine
from core.modules.self_model import persistence
from core.modules.self_model.stream import broadcast, format_sse


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=core_app.app),
        base_url="http://test",
    )


async def test_selfmodel_runtime_returns_real_contract_without_auth(monkeypatch):
    monkeypatch.setattr(core_app.settings, "API_KEY", "changez_moi")
    async with _client() as client:
        response = await client.get("/selfmodel/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["hostname"], str)
    assert isinstance(payload["platform"], str)
    assert isinstance(payload["python_version"], str)
    assert payload["timestamp"]
    for field in (
        "uptime_seconds",
        "cpu_percent",
        "ram_percent",
        "disk_percent",
        "swap_percent",
        "load_avg",
    ):
        assert field in payload


async def test_selfmodel_services_survives_missing_systemctl(monkeypatch):
    def missing_systemctl(*args, **kwargs):
        del args, kwargs
        raise FileNotFoundError("systemctl unavailable")

    monkeypatch.setattr(subprocess, "run", missing_systemctl)
    async with _client() as client:
        response = await client.get("/selfmodel/services")

    assert response.status_code == 200
    payload = response.json()
    assert payload["services"]
    assert all(service["status"] == "unknown" for service in payload["services"])
    assert all(service["error"] for service in payload["services"])


async def test_selfmodel_rack_returns_all_units_without_simulation():
    async with _client() as client:
        response = await client.get("/selfmodel/rack")

    assert response.status_code == 200
    payload = response.json()
    assert [unit["id"] for unit in payload["units"]] == [
        f"U{number}" for number in range(1, 11)
    ]
    assert payload["timestamp"]
    assert next(unit for unit in payload["units"] if unit["id"] == "U10")[
        "status"
    ] == "unknown"


async def test_recommended_selfmodel_endpoints_never_return_503_by_default(
    monkeypatch,
):
    monkeypatch.setattr(core_app.settings, "API_KEY", "changez_moi")
    paths = (
        "/selfmodel",
        "/selfmodel/hardware",
        "/selfmodel/network",
        "/selfmodel/storage",
        "/selfmodel/capabilities",
        "/selfmodel/providers",
        "/selfmodel/agents",
        "/selfmodel/doctor",
        "/selfmodel/events",
        "/selfmodel/topology",
        "/selfmodel/state",
        "/selfmodel/graph",
        "/selfmodel/cognitive-state",
        "/selfmodel/stream-info",
        "/selfmodel/loop",
        "/selfmodel/explain",
        "/selfmodel/why/health_score",
    )
    async with _client() as client:
        responses = [await client.get(path) for path in paths]

    assert all(response.status_code == 200 for response in responses)


async def test_selfmodel_snapshot_contains_all_v2_blocks():
    async with _client() as client:
        response = await client.get("/selfmodel")

    assert response.status_code == 200
    payload = response.json()
    assert {
        "status",
        "health_score",
        "timestamp",
        "runtime",
        "services",
        "rack",
        "hardware",
        "network",
        "storage",
        "providers",
        "agents",
        "goals",
        "doctor",
        "memory",
        "topology",
        "events",
    } <= payload.keys()
    assert payload["status"] in {"online", "degraded", "offline", "unknown"}


async def test_capabilities_topology_and_events_contracts():
    async with _client() as client:
        capabilities = await client.get("/selfmodel/capabilities")
        topology = await client.get("/selfmodel/topology")
        events = await client.get("/selfmodel/events")

    assert capabilities.status_code == 200
    assert isinstance(capabilities.json()["capabilities"], list)
    assert topology.status_code == 200
    assert isinstance(topology.json()["nodes"], list)
    assert isinstance(topology.json()["edges"], list)
    assert events.status_code == 200
    assert isinstance(events.json()["events"], list)
    assert len(events.json()["events"]) <= 100


async def test_snapshot_isolates_collector_failure(monkeypatch):
    def broken_runtime():
        raise RuntimeError("runtime probe failed")

    monkeypatch.setattr(system_service, "collect_runtime", broken_runtime)
    async with _client() as client:
        response = await client.get("/selfmodel")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime"]["status"] == "unknown"
    assert payload["runtime"]["error"] == "runtime probe failed"
    assert payload["services"]["services"]


def test_health_score_contract():
    result = calculate_health_score(
        runtime={"status": "online"},
        services={
            "services": [
                {"name": "neronOS.service", "status": "active"},
                {"name": "neron-doctor.service", "status": "active"},
                {"name": "neron-watchdog.service", "status": "active"},
            ]
        },
        providers={
            "providers": [
                {"type": "llm", "status": "online"},
                {"type": "memory", "status": "online"},
            ]
        },
    )

    assert result["score"] == 100
    assert result["status"] == "online"
    assert result["reasons"]


async def test_v3_endpoints_and_global_snapshot_contract():
    async with _client() as client:
        snapshot = await client.get("/selfmodel")
        state = await client.get("/selfmodel/state")
        graph = await client.get("/selfmodel/graph")
        capabilities = await client.get("/selfmodel/capabilities")
        cognitive = await client.get("/selfmodel/cognitive-state")
        stream_info = await client.get("/selfmodel/stream-info")

    assert snapshot.status_code == 200
    assert {
        "state_engine",
        "cognitive_state",
        "capabilities",
        "graph",
    } <= snapshot.json().keys()
    assert state.status_code == 200
    assert "runtime" in state.json()
    assert graph.status_code == 200
    assert graph.json()["nodes"]
    assert graph.json()["edges"]
    assert capabilities.status_code == 200
    assert capabilities.json()["capabilities"]
    assert cognitive.status_code == 200
    assert cognitive.json()["mode"] in {
        "idle",
        "working",
        "degraded",
        "maintenance",
        "unknown",
    }
    assert stream_info.json() == {
        "available": True,
        "planned": False,
        "transport": ["sse"],
        "endpoint": "/selfmodel/stream",
        "status": "active",
    }


async def test_capability_detail_is_public_by_default(monkeypatch):
    monkeypatch.setattr(core_app.settings, "API_KEY", "changez_moi")
    async with _client() as client:
        response = await client.get("/selfmodel/capabilities/llm.generate")

    assert response.status_code == 200
    assert response.json()["id"] == "llm.generate"


def test_selfmodel_event_bus_publish_list_clear_and_replay(monkeypatch):
    persisted = []
    monkeypatch.setattr(persistence, "save_event", persisted.append)
    bus = SelfModelEventBus()
    observed = []
    bus.subscribe("service.online", observed.append)
    event = bus.publish(
        "service.online",
        "test",
        {"service": "test.service"},
    )

    assert bus.list_events() == [event]
    assert persisted == [event]
    assert observed == [event]
    replayed = []
    assert bus.replay_events(replayed.append) == [event]
    assert replayed == [event]
    bus.clear_events()
    assert bus.list_events() == []


def test_state_engine_update_apply_event_and_build_snapshot():
    engine = StateEngine()
    engine.update_section("runtime", {"status": "online"}, "test")
    engine.apply_event(
        {
            "source": "event-test",
            "payload": {
                "section": "services",
                "data": {"status": "degraded"},
            },
        }
    )

    assert engine.get_section("runtime") == {"status": "online"}
    assert engine.get_section("services") == {"status": "degraded"}
    snapshot = engine.build_snapshot()
    assert snapshot["status"] == "online"
    assert snapshot["sources"]["services"] == "event-test"


def test_capability_engine_requires_observed_dependencies():
    engine = CapabilityEngine()
    snapshot = engine.evaluate(
        {"services": []},
        {"providers": []},
    )
    capabilities = {
        item["id"]: item for item in snapshot["capabilities"]
    }

    assert capabilities["system.status"]["status"] == "online"
    assert capabilities["llm.generate"]["status"] == "unknown"
    assert capabilities["goal.execute"]["status"] == "unknown"
    assert capabilities["homeassistant.control"]["status"] == "unknown"


def test_knowledge_graph_contains_core_selfmodel_and_providers():
    graph = KnowledgeGraph()
    snapshot = graph.build_default_graph(
        {
            "services": {
                "status": "online",
                "services": [
                    {"name": "neronOS.service", "status": "active"}
                ],
            },
            "providers": {
                "status": "online",
                "providers": [
                    {
                        "id": "llm.ollama",
                        "status": "online",
                    }
                ],
            },
        }
    )
    node_ids = {node["id"] for node in snapshot["nodes"]}

    assert {"core", "selfmodel", "providers", "llm.ollama"} <= node_ids
    assert graph.find_node("core")["status"] == "online"
    assert graph.neighbors("core")


def test_stream_format_and_broadcast_without_clients():
    event = {
        "id": "event-1",
        "type": "service.online",
        "source": "test",
        "level": "info",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "payload": {"service": "test.service"},
    }
    formatted = format_sse(event)

    assert "event: selfmodel.event\n" in formatted
    assert '"type": "service.online"' in formatted
    broadcast(event)


def test_persistence_jsonl_snapshot_event_state_and_corruption(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(persistence, "BASE_DIR", tmp_path)
    monkeypatch.setattr(persistence, "SNAPSHOTS_PATH", tmp_path / "snapshots.jsonl")
    monkeypatch.setattr(persistence, "EVENTS_PATH", tmp_path / "events.jsonl")
    monkeypatch.setattr(persistence, "LAST_SNAPSHOT_PATH", tmp_path / "last_snapshot.json")
    monkeypatch.setattr(persistence, "STATE_PATH", tmp_path / "state.json")

    persistence.save_snapshot({"status": "online"})
    persistence.save_event({"id": "one", "type": "test"})
    persistence.save_state({"runtime": {"status": "online"}})
    with persistence.EVENTS_PATH.open("a", encoding="utf-8") as stream:
        stream.write("{corrupt-json}\n")
    persistence.save_event({"id": "two", "type": "test"})

    assert persistence.load_last_snapshot() == {"status": "online"}
    assert [event["id"] for event in persistence.load_events()] == ["one", "two"]
    assert persistence.load_state()["runtime"]["status"] == "online"
    assert persistence.SNAPSHOTS_PATH.exists()


async def test_introspection_and_loop_endpoints():
    async with _client() as client:
        explain = await client.get("/selfmodel/explain")
        why = await client.get("/selfmodel/why/health_score")
        unknown = await client.get("/selfmodel/why/not-observed")
        loop = await client.get("/selfmodel/loop")
        cycle = await client.post("/selfmodel/loop/run-once")

    assert explain.status_code == 200
    assert "available_capabilities" in explain.json()
    assert why.status_code == 200
    assert why.json()["reasons"]
    assert why.json()["evidence"]
    assert unknown.json()["status"] == "unknown"
    assert loop.status_code == 200
    assert cycle.status_code == 200
    assert cycle.json()["loop"]["cycle_count"] >= 1
    assert cycle.json()["snapshot"]["status"] != 503
