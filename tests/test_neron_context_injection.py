from agents.builtin.core import llm_agent


def test_build_prompt_injects_global_neron_context(monkeypatch):
    monkeypatch.setattr(llm_agent, "_get_system_prompt", lambda user_context="": ("SYSTEM", False))
    monkeypatch.setattr(
        llm_agent,
        "build_system_context",
        lambda extra_context=None, include_neron_context=True, force_reload=False: (
            "GLOBAL_CTX\n" + (extra_context or "")
        ),
    )

    prompt = llm_agent._build_prompt("Bonjour")

    assert prompt.startswith("GLOBAL_CTX")
    assert "SYSTEM" in prompt
    assert prompt.endswith("Bonjour")


def test_build_prompt_does_not_duplicate_global_context(monkeypatch):
    monkeypatch.setattr(llm_agent, "_get_system_prompt", lambda user_context="": ("SYSTEM", False))

    calls = {"count": 0}

    def _mock_build_system_context(extra_context=None, include_neron_context=True, force_reload=False):
        calls["count"] += 1
        return "GLOBAL_CTX\n" + (extra_context or "")

    monkeypatch.setattr(llm_agent, "build_system_context", _mock_build_system_context)

    prompt = llm_agent._build_prompt("Salut")

    assert calls["count"] == 1
    assert prompt.count("GLOBAL_CTX") == 1
