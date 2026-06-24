from __future__ import annotations

import asyncio
import inspect
from pathlib import Path


def test_core_modules_self_model_is_importable_and_structured():
    from core.modules.self_model import build_self_model_snapshot, get_self_model_status

    snapshot = build_self_model_snapshot()

    assert set(snapshot) >= {"identity", "memory", "status", "goal", "generated_at"}
    assert isinstance(snapshot["identity"], dict)
    assert isinstance(snapshot["memory"], dict)
    assert isinstance(snapshot["status"], dict)
    assert isinstance(snapshot["goal"], dict)
    assert get_self_model_status()["status"]["core"] == "online"


def test_self_model_has_no_direct_operational_collectors():
    import core.modules.self_model.service as self_model_service

    source = inspect.getsource(self_model_service).lower()

    for forbidden in (
        "import psutil",
        "subprocess",
        "systemctl",
        "prometheus_client",
        "watchdog_agent",
        "doctor.",
        "modules.health",
    ):
        assert forbidden not in source


def test_legacy_self_model_imports_point_to_canonical_module():
    import core.modules.self_model.service as canonical
    import core.self_model.self_model as core_legacy
    import modules.self_model.self_model as modules_legacy

    assert core_legacy.SelfModel is canonical.SelfModel
    assert modules_legacy.SelfModel is canonical.SelfModel
    assert core_legacy.build_self_model_snapshot is canonical.build_self_model_snapshot
    assert modules_legacy.get_self_model is canonical.get_self_model


def test_status_keeps_operational_payload_responsibility():
    from core.modules.status.service import build_status_payload

    payload = build_status_payload()

    assert payload["core"] == "online"
    assert "resources" in payload
    assert "services" in payload
    assert "sources" in payload
    assert payload["sources"]["services"]["status"] == "local_payload"


def test_self_model_routes_use_structured_snapshot():
    from core.api import self_model_context_routes

    status = asyncio.run(self_model_context_routes.self_model_status())
    context = asyncio.run(self_model_context_routes.self_model_context())

    assert "status" in status
    assert "identity" in context
    assert "memory" in context
    assert "status" in context
    assert "goal" in context


def test_self_status_question_routes_to_self_model_not_llm():
    from core.pipeline.orchestrator import CoreOrchestrator

    decision, _ = asyncio.run(
        CoreOrchestrator().decide("Que sais-tu de toi-même ?")
    )

    assert decision.intent == "self_status"
    assert decision.selected_route == "tool_router"


def test_internal_state_question_routes_to_self_model_not_status():
    from core.pipeline.orchestrator import CoreOrchestrator

    decision, _ = asyncio.run(
        CoreOrchestrator().decide("Quel est ton état interne ?")
    )

    assert decision.intent == "self_status"
    assert decision.selected_route == "tool_router"


def test_self_model_reports_goal_and_task_anomalies(monkeypatch):
    import core.modules.self_model.service as service

    monkeypatch.setattr(
        service,
        "_safe_goal_runtime",
        lambda: {
            "active_goal": {"id": "goal-test", "status": "active"},
            "runtime_status": {"status": "interrupted"},
        },
    )
    monkeypatch.setattr(
        service,
        "_safe_task_state",
        lambda: {
            "summary": {
                "total": 4,
                "active": 1,
                "pending": 0,
                "running": 0,
                "failed": 3,
            }
        },
    )

    snapshot = service.build_self_model_snapshot()

    assert snapshot["health_global"] == "stable_with_warning"
    assert snapshot["cognitive_state"]["state"] == "warning"
    assert any("interrupted" in item for item in snapshot["diagnostics"])
    assert any("3 tâche(s) en échec" in item for item in snapshot["diagnostics"])
    assert snapshot["tasks"]["summary"]["failed"] == 3


def test_self_model_source_does_not_reintroduce_old_direct_collectors():
    root = Path(__file__).parents[1] / "core" / "modules" / "self_model"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))

    assert "psutil" not in text
    assert "systemctl" not in text
    assert "prometheus_client" not in text
