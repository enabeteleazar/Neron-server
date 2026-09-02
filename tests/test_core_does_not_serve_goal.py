"""Phase 2E : Core ne sert pas Goal.

Core montait `goal.goals.routes` et `goal.projects.routes` dans sa propre
application : les deux process repondaient aux memes routes, avec deux jeux de
singletons (GoalManager, TaskManager, PlanStorage) au-dessus du MEME stockage,
sans verrou inter-process. `POST /goal` recu par Core creait de vraies
asyncio.Task Goal dans le process Core.

Ce couplage etait invisible pour le cliquet de `test_architecture_boundaries`,
qui compte des imports AST : le montage passait par
`importlib.import_module("goal.goals.routes")` — une CHAINE, pas un import.
D ou ce test dedie.

Regle : Goal:8030 est l unique proprietaire de l API Goal ; Core y accede par
`server.common.goal_client`.
"""

from __future__ import annotations

from core import app as core_app

# Routes servies par goal/goals/routes.py et goal/projects/routes.py.
# `/goals/active/task` n y figure pas : elle vient de core/api/goal_task_routes.py
# (route Core native, conservee).
GOAL_OWNED_PATHS = {
    "/goal",
    "/goals",
    "/goals/run",
    "/goals/active",
    "/goal/{goal_id}/status",
    "/goal/{goal_id}/events",
    "/goals/{goal_id}/complete",
    "/goals/{goal_id}/fail",
    "/goals/{goal_id}/progress",
    "/projects",
    "/projects/search",
    "/projects/diagnostics/failures",
    "/projects/{project_id}",
    "/agents/build",
    "/agents/registry/scan",
    "/agents/registry/index",
    "/agents/registry/diagnostics",
    "/agents/{agent_name}/status",
    "/agents/{agent_name}/inspect",
    "/agents/{agent_name}/revise",
    "/agents/{agent_name}/update",
    "/agents/{agent_name}/rename",
    "/agents/{agent_name}/delete",
    "/agents/{agent_name}/rollback",
}


def _core_paths() -> set[str]:
    return {
        route.path
        for route in core_app.app.routes
        if getattr(route, "path", None)
    }


def test_core_does_not_expose_goal_owned_routes():
    served = _core_paths() & GOAL_OWNED_PATHS

    assert served == set(), (
        "Core sert des routes qui appartiennent a Goal:8030 : "
        f"{sorted(served)}. Core ne doit pas servir Goal."
    )


def test_core_does_not_mount_any_goal_router():
    """Le montage se fait par nom de module : c est la chaine qu il faut verifier."""
    goal_specs = [
        spec
        for spec in core_app._EXTERNAL_ROUTER_SPECS
        if spec[1].split(".")[0] == "goal"
    ]

    assert goal_specs == [], (
        f"routers Goal encore montes par Core : {goal_specs}"
    )


def test_core_native_goal_task_route_is_preserved():
    """Garde-fou inverse : ne pas retirer une route qui appartient a Core."""
    assert "/goals/active/task" in _core_paths()
