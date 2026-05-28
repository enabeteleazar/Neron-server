from core.agents.core import llm_agent


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
