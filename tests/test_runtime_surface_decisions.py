from __future__ import annotations


def test_core_app_uses_official_world_model_router_and_main_telegram_surface():
    import core.app as app
    from agents.builtin.communication import telegram_agent
    from core.api import world_model_routes

    route_paths = {route.path for route in app.app.routes}

    assert app.world_model_router is world_model_routes.router
    assert "/world-model/status" in route_paths
    assert app.start_bot is telegram_agent.start_bot


def test_legacy_world_model_api_is_not_registered_in_core_app():
    import core.app as app
    from modules.memory.world_model.api import world_model_router as legacy_world_model_router

    active_route_names = {getattr(route, "name", "") for route in app.app.routes}
    legacy_route_names = {getattr(route, "name", "") for route in legacy_world_model_router.routes}

    assert active_route_names.isdisjoint(legacy_route_names)
