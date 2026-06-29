from __future__ import annotations

import httpx

from core.api import auth
from core.infrastructure.event_bus import event_bus
from modules.evolution import routes as evolution_routes
from core import app as core_app


API_KEY = "internal-test-key"


def _set_api_key(monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "API_KEY", API_KEY)
    monkeypatch.setattr(core_app.settings, "API_KEY", API_KEY)
    monkeypatch.setattr(core_app, "world_model", type("WorldModel", (), {"get": lambda self: {"ok": True}})())

    class _Supervisor:
        def status(self):
            return {"active_run": None, "recent_runs": []}

    monkeypatch.setattr(evolution_routes, "get_evolution_supervisor", lambda: _Supervisor())


def _client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=core_app.app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def test_internal_orchestration_endpoints_reject_missing_api_key(monkeypatch):
    _set_api_key(monkeypatch)

    async with _client() as client:
        for path in ("/planner/status", "/tasks/status", "/evolution/status", "/projects"):
            response = await client.get(path)
            assert response.status_code == 401, path
            assert response.json()["detail"] == "API Key manquante"


async def test_internal_orchestration_endpoints_reject_invalid_api_key(monkeypatch):
    _set_api_key(monkeypatch)

    async with _client() as client:
        response = await client.get("/planner/status", headers={"X-API-Key": "wrong"})

    assert response.status_code == 403
    assert response.json()["detail"] == "API Key invalide"


async def test_internal_orchestration_endpoints_accept_valid_api_key(monkeypatch):
    _set_api_key(monkeypatch)
    headers = {"X-API-Key": API_KEY}

    timeout = httpx.Timeout(3.0)
    async with _client() as client:
        client.timeout = timeout
        for path in ("/planner/status", "/tasks/status", "/evolution/status", "/projects"):
            response = await client.get(path, headers=headers)
            assert response.status_code == 200, f"{path}: {response.text}"


async def test_public_health_endpoints_remain_accessible_without_api_key(monkeypatch):
    _set_api_key(monkeypatch)

    async with _client() as client:
        health = await client.get("/health")
        root = await client.get("/")
        status = await client.get("/status")

    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert root.status_code == 401
    assert status.status_code == 401


async def test_api_key_empty_is_rejected(monkeypatch):
    _set_api_key(monkeypatch)

    async with _client() as client:
        response = await client.get(
            "/self-model/context",
            headers={"X-API-Key": ""},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "API Key manquante"


async def test_default_api_key_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(auth.settings, "API_KEY", "changez_moi")
    monkeypatch.setattr(core_app.settings, "API_KEY", "changez_moi")

    async with _client() as client:
        response = await client.get(
            "/self-model/context",
            headers={"X-API-Key": "changez_moi"},
        )
        health = await client.get("/health")

    assert response.status_code == 503
    assert response.json()["detail"] == "Authentification API non configurée"
    assert health.status_code == 200


async def test_sensitive_routes_are_never_public(monkeypatch):
    _set_api_key(monkeypatch)
    sensitive_paths = (
        "/self-model/context",
        "/memory/status",
        "/code-awareness/map",
        "/cognitive-core/state",
        "/actions/latest",
        "/critic/latest",
        "/world-model/status",
        "/runtime/governor/policy",
        "/registry/services",
        "/gateway/doctor/health",
        "/goals",
    )

    async with _client() as client:
        for path in sensitive_paths:
            response = await client.get(path)
            assert response.status_code == 401, path


async def test_sensitive_route_accepts_valid_api_key(monkeypatch):
    _set_api_key(monkeypatch)

    async with _client() as client:
        response = await client.get(
            "/self-model/context",
            headers={"X-API-Key": API_KEY},
        )

    assert response.status_code == 200


async def test_official_and_legacy_headers_and_auth_events(monkeypatch):
    _set_api_key(monkeypatch)
    event_bus.clear()

    async with _client() as client:
        invalid = await client.get(
            "/status",
            headers={
                "X-Neron-API-Key": "wrong",
                "X-Neron-Trace-Id": "trace-auth-failure",
            },
        )
        official = await client.get(
            "/status",
            headers={
                "X-Neron-API-Key": API_KEY,
                "X-Neron-Trace-Id": "trace-auth-official",
            },
        )
        legacy = await client.get(
            "/status",
            headers={
                "X-API-Key": API_KEY,
                "X-Neron-Trace-Id": "trace-auth-legacy",
            },
        )
        failures = await client.get(
            "/events",
            params={"event_type": "auth.failure"},
            headers={"X-Neron-API-Key": API_KEY},
        )
        successes = await client.get(
            "/events",
            params={"event_type": "auth.success"},
            headers={"X-Neron-API-Key": API_KEY},
        )

    assert invalid.status_code == 403
    assert official.status_code == 200
    assert legacy.status_code == 200

    failure_events = failures.json()["events"]
    assert failure_events[-1]["trace_id"] == "trace-auth-failure"
    assert failure_events[-1]["payload"]["reason"] == "invalid"
    assert failure_events[-1]["level"] == "warning"

    success_events = successes.json()["events"]
    assert any(
        event["trace_id"] == "trace-auth-official"
        and event["payload"]["header"] == "X-Neron-API-Key"
        for event in success_events
    )
    assert any(
        event["trace_id"] == "trace-auth-legacy"
        and event["payload"]["header"] == "X-API-Key"
        for event in success_events
    )
