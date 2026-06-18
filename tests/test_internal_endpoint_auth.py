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

    assert core_app.root()["status"] == "active"
    assert core_app.health()["status"] == "healthy"
    assert core_app.status() == {"ok": True}
