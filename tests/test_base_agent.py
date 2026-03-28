# tests/test_base_agent.py
# Tests pour core/agents/base_agent.py

import pytest
from core.agents.base_agent import BaseAgent, AgentResult


class TestAgentResult:
    def test_agent_result_creation(self):
        result = AgentResult(
            success=True,
            content="test content",
            intent="test_intent",
            agent="test_agent"
        )
        assert result.success is True
        assert result.content == "test content"
        assert result.intent == "test_intent"
        assert result.agent == "test_agent"

    def test_agent_result_defaults(self):
        result = AgentResult()
        assert result.success is False
        assert result.content == ""
        assert result.intent == ""
        assert result.agent == ""


class MockAgent(BaseAgent):
    def __init__(self, name="mock"):
        super().__init__(name)

    async def execute(self, query: str, **kwargs):
        return AgentResult(
            success=True,
            content=f"Mock response to: {query}",
            intent="mock",
            agent=self.name
        )


class TestBaseAgent:
    @pytest.fixture
    def agent(self):
        return MockAgent("test_agent")

    def test_agent_initialization(self, agent):
        assert agent.name == "test_agent"
        assert agent.logger is not None

    @pytest.mark.asyncio
    async def test_execute_not_implemented(self):
        agent = BaseAgent("base")
        with pytest.raises(NotImplementedError):
            await agent.execute("test")

    @pytest.mark.asyncio
    async def test_mock_execute(self, agent):
        result = await agent.execute("hello")
        assert result.success is True
        assert "hello" in result.content
        assert result.agent == "test_agent"

    def test_failure_method(self, agent):
        result = agent._failure("error message")
        assert result.success is False
        assert result.content == "error message"
        assert result.intent == "error"
        assert result.agent == "test_agent"