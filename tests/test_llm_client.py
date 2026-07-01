from __future__ import annotations

import pytest

from llm.core.types import LLMResponse
from llm.client.client import NéronLLMClient


class FakeManager:
    response = LLMResponse(
        response="ok",
        model="test-model",
        provider="test-provider",
    )
    request = None

    async def handle(self, request):
        self.__class__.request = request
        return self.__class__.response

    async def aclose(self):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_warning",
    [
        "LLM authentication rejected (HTTP 403)",
        "LLM endpoint not found (HTTP 404)",
        "LLM request validation failed (HTTP 422)",
        "LLM provider failure (HTTP 502)",
    ],
)
async def test_llm_client_preserves_manager_failure_kind(expected_warning: str):
    client = NéronLLMClient()
    FakeManager.response = LLMResponse(
        response="",
        model="degraded",
        provider="test-provider",
        error=expected_warning,
    )
    client.manager = FakeManager()
    result = await client.generate(prompt="test")

    assert result.model_used == "degraded"
    assert result.warning == expected_warning


@pytest.mark.asyncio
async def test_llm_client_translates_request_for_current_manager():
    client = NéronLLMClient()
    FakeManager.response = LLMResponse(
        response="ok",
        model="test-model",
        provider="test-provider",
    )
    FakeManager.request = None
    client.manager = FakeManager()
    result = await client.generate(task_type="reasoning", prompt="test")

    assert result.result == "ok"
    assert FakeManager.request.task == "reasoning"
    assert FakeManager.request.message == "test"
