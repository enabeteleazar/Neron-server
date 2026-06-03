# tests/test_base_agent.py
"""Tests unitaires — BaseAgent, AgentResult, types LLM"""

import time
import pytest
from core.agents.base_agent import (
    AgentResult, BaseAgent, get_logger,
    register_agent, get_agents, _agents,
)
from core.llm_client.types import (
    LLMGenerateRequest, LLMGenerateResponse, DEGRADED_RESPONSE, TaskType,
)


# ── AgentResult ────────────────────────────────────────────────────────────────

class TestAgentResult:
    def test_success_defaults(self):
        r = AgentResult(success=True, content="ok", source="test")
        assert r.success is True
        assert r.intent == "unknown"
        assert r.confidence == "low"
        assert r.error is None
        assert r.metadata == {}

    def test_failure_defaults(self):
        r = AgentResult(success=False, content="", source="test", error="boom")
        assert r.success is False
        assert r.error == "boom"

    def test_full_fields(self):
        r = AgentResult(
            success=True, content="data", source="s",
            intent="web_search", confidence="high",
            metadata={"k": "v"}, latency_ms=42.5,
        )
        assert r.intent == "web_search"
        assert r.confidence == "high"
        assert r.latency_ms == 42.5
        assert r.metadata["k"] == "v"


# ── ConcreteAgent (implémentation minimale pour les tests) ────────────────────

class ConcreteAgent(BaseAgent):
    async def execute(self, query: str, **kwargs) -> AgentResult:
        return self._success(f"réponse à : {query}", confidence="high")


class FailingAgent(BaseAgent):
    async def execute(self, query: str, **kwargs) -> AgentResult:
        return self._failure("erreur intentionnelle")


# ── BaseAgent helpers ──────────────────────────────────────────────────────────

class TestBaseAgentHelpers:
    def test_success_result(self):
        agent = ConcreteAgent("test_agent")
        r = agent._success("contenu", metadata={"k": 1}, latency_ms=10.0, confidence="high")
        assert r.success is True
        assert r.content == "contenu"
        assert r.source == "test_agent"
        assert r.confidence == "high"
        assert r.latency_ms == 10.0
        assert r.metadata == {"k": 1}

    def test_success_no_metadata(self):
        agent = ConcreteAgent("a")
        r = agent._success("x")
        assert r.metadata == {}

    def test_failure_result(self):
        agent = FailingAgent("fail_agent")
        r = agent._failure("boom", latency_ms=5.0)
        assert r.success is False
        assert r.content == ""
        assert r.error == "boom"
        assert r.source == "fail_agent"
        assert r.latency_ms == 5.0

    def test_timer_and_elapsed(self):
        agent = ConcreteAgent("timer_agent")
        start = agent._timer()
        time.sleep(0.01)
        elapsed = agent._elapsed_ms(start)
        assert elapsed >= 10.0
        assert elapsed < 500.0

    @pytest.mark.asyncio
    async def test_execute(self):
        agent = ConcreteAgent("exec_agent")
        r = await agent.execute("hello")
        assert r.success is True
        assert "hello" in r.content

    @pytest.mark.asyncio
    async def test_on_start_noop(self):
        agent = ConcreteAgent("start_agent")
        await agent.on_start()  # ne doit pas lever d'exception


# ── register_agent / get_agents ────────────────────────────────────────────────

class TestAgentRegistry:
    def setup_method(self):
        _agents.clear()

    def test_register_and_get(self):
        agent = ConcreteAgent("reg_agent")
        register_agent(agent)
        agents = get_agents()
        assert "reg_agent" in agents
        assert agents["reg_agent"] is agent

    def test_multiple_agents(self):
        a1 = ConcreteAgent("agent_a")
        a2 = FailingAgent("agent_b")
        register_agent(a1)
        register_agent(a2)
        agents = get_agents()
        assert len(agents) == 2

    def test_overwrite_same_name(self):
        a1 = ConcreteAgent("dup")
        a2 = ConcreteAgent("dup")
        register_agent(a1)
        register_agent(a2)
        assert get_agents()["dup"] is a2


# ── get_logger ─────────────────────────────────────────────────────────────────

class TestGetLogger:
    def test_returns_logger(self):
        import logging
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)

    def test_idempotent(self):
        l1 = get_logger("test.idempotent")
        l2 = get_logger("test.idempotent")
        assert l1 is l2

    def test_custom_level(self):
        import logging
        logger = get_logger("test.level", level=logging.DEBUG)
        assert logger.level == logging.DEBUG


# ── LLM Types ─────────────────────────────────────────────────────────────────

class TestLLMTypes:
    def test_generate_request_defaults(self):
        req = LLMGenerateRequest(prompt="test")
        assert req.task_type == "chat"
        assert req.model_preference == "auto"
        assert req.request_id == ""
        assert req.context == {}

    def test_generate_request_full(self):
        req = LLMGenerateRequest(
            task_type="code",
            prompt="écris une fonction",
            context={"lang": "python"},
            model_preference="qwen2.5-coder:14b",
            request_id="req-001",
        )
        assert req.task_type == "code"
        assert req.context["lang"] == "python"

    def test_generate_response(self):
        resp = LLMGenerateResponse(result="bonjour", model_used="llama3.2", latency_ms=250)
        assert resp.result == "bonjour"
        assert resp.warning is None

    def test_degraded_response_sentinel(self):
        assert DEGRADED_RESPONSE.model_used == "degraded"
        assert DEGRADED_RESPONSE.latency_ms == 0
        assert DEGRADED_RESPONSE.warning is not None
        assert len(DEGRADED_RESPONSE.result) > 0

    @pytest.mark.parametrize("task", ["code", "reasoning", "chat", "agent"])
    def test_valid_task_types(self, task):
        req = LLMGenerateRequest(prompt="p", task_type=task)
        assert req.task_type == task
