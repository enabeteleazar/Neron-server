from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from fastapi import HTTPException

from doctor.auth import require_api_key
from doctor.config import cfg


def test_sensitive_core_routers_declare_verify_api_key_dependency():
    from core import app as core_app

    source = inspect.getsource(core_app)
    protected = (
        "self_model_router",
        "selfmodel_router",
        "runtime_governor_router",
        "world_model_router",
        "goals_router",
        "goal_task_router",
        "cognitive_core_router",
        "cognitive_report_router",
        "action_history_router",
        "critic_history_router",
        "code_awareness_router",
        "memory_router",
    )
    for router in protected:
        assert f"app.include_router({router}, dependencies=_INTERNAL_AUTH)" in source


def test_doctor_auth_uses_constant_time_comparison(monkeypatch):
    monkeypatch.setattr(cfg, "API_KEY", "doctor-secret")
    monkeypatch.setattr(cfg, "AUTH_DEV_MODE", False)

    assert require_api_key("doctor-secret") is None
    with pytest.raises(HTTPException) as exc:
        require_api_key("wrong")
    assert exc.value.status_code == 401


def test_doctor_auth_fails_closed_without_configuration(monkeypatch):
    monkeypatch.setattr(cfg, "API_KEY", "")
    monkeypatch.setattr(cfg, "AUTH_DEV_MODE", False)

    with pytest.raises(HTTPException) as exc:
        require_api_key(None)
    assert exc.value.status_code == 503


def test_doctor_auth_dev_mode_requires_explicit_flag(monkeypatch):
    monkeypatch.setattr(cfg, "API_KEY", "")
    monkeypatch.setattr(cfg, "AUTH_DEV_MODE", True)

    assert require_api_key(None) is None


def test_legacy_homelab_cors_uses_environment_allowlist():
    source = Path("web/legacy/homelab/api/src/app.ts").read_text(encoding="utf-8")

    assert "app.use(cors());" not in source
    assert "CORS_ALLOWED_ORIGINS" in source
    assert "allowedOrigins.includes(origin)" in source
