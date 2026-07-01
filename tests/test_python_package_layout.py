from __future__ import annotations

import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "server"


def test_core_modules_resolve_from_single_explicit_package():
    for module_name in (
        "core",
        "core.a2a",
        "core.pipeline",
        "core.goal_engine",
        "core.modules",
        "core.runtime",
    ):
        spec = importlib.util.find_spec(module_name)

        assert spec is not None
        assert spec.origin is not None, f"{module_name} is an implicit namespace"
        assert Path(spec.origin).is_relative_to(SERVER_ROOT / "core")


def test_goal_resolves_from_explicit_server_package():
    spec = importlib.util.find_spec("goal")

    assert spec is not None
    assert spec.origin == str(SERVER_ROOT / "goal" / "__init__.py")


def test_repository_root_does_not_shadow_core_package():
    assert not (PROJECT_ROOT / "core").exists()
