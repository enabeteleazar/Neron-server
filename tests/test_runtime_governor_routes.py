from core.api import runtime_governor_routes


async def test_runtime_governor_policy_exposes_global_context(monkeypatch):
    class _Governor:
        def to_dict(self):
            return {"runtime_mode": "normal"}

    monkeypatch.setattr(runtime_governor_routes, "get_runtime_governor", lambda: _Governor())
    monkeypatch.setattr(
        runtime_governor_routes,
        "get_neron_context_status",
        lambda: {"exists": True, "path": "/etc/neron/NERON.md"},
    )

    payload = await runtime_governor_routes.runtime_governor_policy()

    assert payload["policy"]["runtime_mode"] == "normal"
    assert payload["global_context"]["exists"] is True
