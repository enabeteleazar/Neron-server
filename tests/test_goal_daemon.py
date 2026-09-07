from __future__ import annotations

import asyncio
import os
import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from goal import app as goal_app


@pytest.fixture(autouse=True)
def clear_goal_store():
    """Isole chaque test du stock d'objectifs.

    `goal.app` n'expose plus de `goal_store` : les objectifs vivent dans un
    GoalManager singleton (goal.goals.goal_manager), adosse a un fichier
    d'etat JSON et a SQLite. On remet le singleton a zero et on efface
    l'etat persiste, dont conftest.py a deja detourne le chemin vers un
    repertoire temporaire.
    """
    from goal.goals import goal_manager as goal_manager_module
    from goal.goals import persistence

    def _reset() -> None:
        goal_manager_module._GOAL_MANAGER = None
        persistence.GOALS_PATH.unlink(missing_ok=True)
        # Les objectifs vivent aussi en SQLite et dans le moteur
        # d'execution : sans ce nettoyage, ceux crees par les autres
        # fichiers de test fuient ici (constate : goal_count=9 au lieu de 0).
        try:
            from goal.goals.goal_manager import GoalManager

            store = GoalManager().sqlite_store
            with store._transaction() as connection:
                connection.execute("DELETE FROM goals")
        except Exception:
            pass
        try:
            from goal.goals.routes import get_goal_execution_engine

            engine = get_goal_execution_engine()
            for attribut in ("_goals", "_runs", "goals"):
                cible = getattr(engine, attribut, None)
                if hasattr(cible, "clear"):
                    cible.clear()
        except Exception:
            pass

    _reset()
    # Le transport ASGI ne declenche pas le lifespan : on pose l'etat que
    # /health et /status attendent (cf. server/common/service.py).
    goal_app.app.state.started_at = time.monotonic()
    goal_app.app.state.registry_client = None
    yield
    _reset()


def _client() -> httpx.AsyncClient:
    # Les routes /goals portent require_api_key (goal.infra.security) : sans
    # en-tete elles repondent 401 avant meme la validation du corps.
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=goal_app.app),
        base_url="http://goal.test",
        headers={"Authorization": f"Bearer {os.environ['NERON_API_KEY']}"},
    )


@pytest.mark.asyncio
async def test_health_and_status():
    async with _client() as client:
        health = await client.get("/health")
        status = await client.get("/status")

    # /health renvoie desormais la charge standard de create_service_app
    # (service, status, version, uptime_s, registered).
    corps = health.json()
    assert corps["service"] == "goal"
    assert corps["status"] == "healthy"
    assert status.status_code == 200
    assert status.json()["service"] == "goal"
    assert status.json()["status"] == "running"
    assert status.json()["uptime"] >= 0
    assert status.json()["goal_count"] == 0


@pytest.mark.asyncio
async def test_goal_mvp_lifecycle():
    async with _client() as client:
        created = await client.post(
            "/goals",
            json={
                "title": "Tester le daemon",
                "description": "MVP",
                "priority": "high",
            },
        )
        goal = created.json()["goal"]
        listed = await client.get("/goals")
        # GET /goals/{id} et POST /goals/{id}/cancel n'existent plus :
        # la consultation passe par /goal/{id}/status et la cloture par
        # /goals/{id}/complete (ou /fail).
        fetched = await client.get(f"/goal/{goal['id']}/status")
        completed = await client.post(f"/goals/{goal['id']}/complete")

    assert created.status_code == 200
    # Un objectif nait "pending" ; "queued" est un etat du moteur d execution.
    assert goal["status"] == "pending"
    assert listed.json()["count"] == 1
    assert fetched.status_code == 200
    assert completed.json()["goal"]["status"] == "completed"


@pytest.mark.asyncio
async def test_goal_routes_reject_invalid_and_missing_goals():
    async with _client() as client:
        invalid = await client.post("/goals", json={"title": "   "})
        missing = await client.get("/goals/missing")
        cancel_missing = await client.post("/goals/missing/cancel")

    assert invalid.status_code == 422
    assert missing.status_code == 404
    assert cancel_missing.status_code == 404


def test_goal_registry_payload_uses_common_sdk():
    """Goal s'annonce au registre avec le bon nom et les bonnes capacites.

    `goal.app` n'a plus ni RegistryClient ni create_registry_client : la
    construction du client d'enregistrement a ete centralisee dans
    server/common/service.py (create_service_app). On patche donc la ou le
    client est reellement construit.
    """
    import server.common.service as service_module

    with patch.object(service_module, "RegistryClient") as client_class:
        client_class.return_value.start = AsyncMock()
        client_class.return_value.stop = AsyncMock()

        async def _monter():
            async with goal_app.app.router.lifespan_context(goal_app.app):
                pass

        asyncio.run(_monter())

    kwargs = client_class.call_args.kwargs
    assert kwargs["service_name"] == "goal"
    assert kwargs["capabilities"] == [
        "goal_execution",
        "planning",
        "agent_creation",
        "task_loop",
    ]


@pytest.mark.asyncio
async def test_goal_lifespan_starts_and_stops_registry():
    """Le client de registre est demarre puis arrete par le lifespan."""
    import server.common.service as service_module

    registry = Mock()
    registry.start = AsyncMock()
    registry.stop = AsyncMock()

    with patch.object(service_module, "RegistryClient", return_value=registry):
        async with goal_app.app.router.lifespan_context(goal_app.app):
            registry.start.assert_awaited_once()
            assert goal_app.app.state.registry_client is registry

    registry.stop.assert_awaited_once()
