from __future__ import annotations


def test_watchdog_uses_canonical_world_model_singleton():
    from agents.builtin.automation import watchdog_agent
    from modules.world_model.world_model import get_world_model

    assert watchdog_agent.world_model is get_world_model()


def test_legacy_world_model_import_is_a_compatibility_adapter():
    from modules.memory.world_model.world_model import WorldModel as LegacyWorldModel
    from modules.world_model.world_model import WorldModel

    assert LegacyWorldModel is WorldModel


def test_world_model_observations_are_kept_in_world_model():
    from modules.world_model.world_model import WorldModel

    model = WorldModel()
    model.update("agents", "memory", {"status": "online"})

    assert model.get_category("agents")["memory"]["status"] == "online"
    assert model.to_dict()["observations"]["agents"]["memory"]["status"] == "online"


def test_self_model_summary_does_not_embed_world_model(monkeypatch, tmp_path):
    from core.self_model import self_model

    state_path = tmp_path / "self_model_state.json"
    monkeypatch.setattr(self_model, "STATE_PATH", state_path)

    model = self_model.SelfModel()
    model.refresh()
    summary = model.summary()

    assert "État interne de Néron" in summary
    assert "Monde externe" not in summary
