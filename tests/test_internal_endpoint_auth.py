from __future__ import annotations

import httpx

from core.api import auth
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
        # Phase 2E : "/projects" retire de l echantillon — cette route
        # appartient a Goal:8030 et n est plus servie par Core.
        for path in ("/planner/status", "/tasks/status", "/evolution/status"):
            response = await client.get(path)
            assert response.status_code == 401, path
            assert response.json()["detail"] == "API Key manquante"


async def test_internal_orchestration_endpoints_reject_invalid_api_key(monkeypatch):
    _set_api_key(monkeypatch)

    async with _client() as client:
        response = await client.get("/planner/status", headers={"Authorization": "Bearer wrong"})

    assert response.status_code == 403
    assert response.json()["detail"] == "API Key invalide"


async def test_internal_orchestration_endpoints_accept_valid_api_key(monkeypatch):
    _set_api_key(monkeypatch)
    headers = {"Authorization": f"Bearer {API_KEY}"}

    timeout = httpx.Timeout(3.0)
    async with _client() as client:
        client.timeout = timeout
        # Phase 2E : "/projects" retire de l echantillon — cette route
        # appartient a Goal:8030 et n est plus servie par Core.
        for path in ("/planner/status", "/tasks/status", "/evolution/status"):
            response = await client.get(path, headers=headers)
            assert response.status_code == 200, f"{path}: {response.text}"


async def test_internal_endpoints_accept_authorization_bearer_api_key(monkeypatch):
    _set_api_key(monkeypatch)

    async with _client() as client:
        response = await client.get(
            "/planner/status",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

    assert response.status_code == 200, response.text


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
            headers={"Authorization": "Bearer "},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "API Key manquante"


async def test_default_api_key_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(auth.settings, "API_KEY", "changez_moi")
    monkeypatch.setattr(core_app.settings, "API_KEY", "changez_moi")

    async with _client() as client:
        response = await client.get(
            "/self-model/context",
            headers={"Authorization": "Bearer changez_moi"},
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
        "/cognitive-core/report",
        "/actions/latest",
        "/critic/latest",
        "/world-model/status",
        "/runtime/governor/policy",
        # Phase 2E : "/goals" retire — appartient a Goal:8030.
        # "/goals/active/task" (route Core native) reste couverte plus bas.
    )

    async with _client() as client:
        for path in sensitive_paths:
            response = await client.get(path)
            assert response.status_code == 401, path


async def test_all_explicitly_protected_router_surfaces_reject_bad_key(monkeypatch):
    _set_api_key(monkeypatch)
    requests = (
        ("GET", "/self-model/status"),
        ("GET", "/runtime/governor/policy"),
        ("GET", "/world-model/status"),
        ("POST", "/goals/active/task"),
        ("GET", "/cognitive-core/state"),
        ("GET", "/cognitive-core/report"),
        ("GET", "/actions/latest"),
        ("GET", "/critic/latest"),
        ("GET", "/code-awareness/map"),
        ("GET", "/memory/status"),
    )

    async with _client() as client:
        for method, path in requests:
            response = await client.request(
                method,
                path,
                headers={"Authorization": "Bearer wrong"},
            )
            assert response.status_code == 403, (method, path, response.text)


async def test_sensitive_route_accepts_valid_api_key(monkeypatch):
    _set_api_key(monkeypatch)

    async with _client() as client:
        response = await client.get(
            "/self-model/context",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

    assert response.status_code == 200
