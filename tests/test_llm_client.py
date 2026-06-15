from __future__ import annotations

import httpx
import pytest

from llm.client.client import NéronLLMClient


class FakeAsyncClient:
    status_code = 200
    request_headers: dict[str, str] = {}

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url: str, *, content: str, headers: dict[str, str]):
        self.__class__.request_headers = headers
        request = httpx.Request("POST", url)
        if self.status_code != 200:
            return httpx.Response(
                self.status_code,
                request=request,
                json={"detail": "request rejected"},
            )
        return httpx.Response(
            200,
            request=request,
            json={
                "result": "ok",
                "model_used": "test-model",
                "latency_ms": 1,
                "warning": None,
            },
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_warning"),
    [
        (403, "LLM authentication rejected (HTTP 403)"),
        (404, "LLM endpoint not found (HTTP 404)"),
        (422, "LLM request validation failed (HTTP 422)"),
        (502, "LLM provider failure (HTTP 502)"),
    ],
)
async def test_llm_client_preserves_http_failure_kind(
    monkeypatch,
    status_code: int,
    expected_warning: str,
):
    FakeAsyncClient.status_code = status_code
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = NéronLLMClient()
    client._retries = 0
    result = await client.generate(prompt="test")

    assert result.model_used == "degraded"
    assert result.warning == expected_warning


@pytest.mark.asyncio
async def test_llm_client_uses_internal_api_key_header(monkeypatch):
    FakeAsyncClient.status_code = 200
    FakeAsyncClient.request_headers = {}
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = NéronLLMClient()
    client._api_key = "test-only-key"
    result = await client.generate(prompt="test")

    assert result.result == "ok"
    assert FakeAsyncClient.request_headers["X-Neron-API-Key"] == "test-only-key"
    assert "X-API-Key" not in FakeAsyncClient.request_headers
