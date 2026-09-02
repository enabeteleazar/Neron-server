"""Phase 2D : `POST /planner/from-goal` lit l objectif actif via GoalClient.

Avant : `get_goal_manager().get_active_goal()` — un GoalManager de Goal importe
en process dans Core, avec son propre etat.
Apres : `await get_goal_client().get_active_goal()` — HTTP vers goal:8030, la
source de verite.

Seuls les deux chemins qui n atteignent PAS `planner.create_plan()` sont
testes ici : celui-ci declencherait une vraie planification (LLM, ecriture
disque). C est exactement le perimetre de ce qui a ete modifie.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from core.api import planner_routes
from server.common.goal_client import GoalClientError


class _FakeGoalClient:
    def __init__(self, *, active_goal=None, error: Exception | None = None) -> None:
        self._active_goal = active_goal
        self._error = error
        self.calls = 0

    async def get_active_goal(self):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._active_goal


async def test_returns_404_when_goal_service_reports_no_active_goal(monkeypatch):
    client = _FakeGoalClient(active_goal=None)
    monkeypatch.setattr(
        "server.common.goal_client.get_goal_client", lambda: client
    )

    with pytest.raises(HTTPException) as excinfo:
        await planner_routes.planner_from_goal()

    assert excinfo.value.status_code == 404
    assert client.calls == 1, "l objectif actif doit etre lu via GoalClient"


async def test_returns_503_when_goal_service_is_unreachable(monkeypatch):
    """Une panne reseau ne doit pas se confondre avec « aucun objectif actif »."""
    client = _FakeGoalClient(error=GoalClientError("connexion refusee"))
    monkeypatch.setattr(
        "server.common.goal_client.get_goal_client", lambda: client
    )

    with pytest.raises(HTTPException) as excinfo:
        await planner_routes.planner_from_goal()

    assert excinfo.value.status_code == 503


def test_planner_routes_no_longer_imports_the_goal_manager():
    """Le decouplage doit rester : pas de retour a un import interne de Goal."""
    source = planner_routes.__file__
    with open(source, encoding="utf-8") as handle:
        content = handle.read()

    assert "from goal.goals.goal_manager import" not in content
