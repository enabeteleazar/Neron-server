# tests/test_web_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from agents.web_agent import WebAgent


def make_mock_client(json_data=None, status_code=200, raise_exc=None):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data or {}
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="error", request=MagicMock(), response=mock_response
        )
    else:
        mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    if raise_exc:
        mock_client.get = AsyncMock(side_effect=raise_exc)
    else:
        mock_client.get = AsyncMock(return_value=mock_response)
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


@pytest.mark.asyncio
async def test_web_agent_success(mock_searxng_response):
    agent = WebAgent()
    with patch("httpx.AsyncClient", return_value=make_mock_client(mock_searxng_response)):
        result = await agent.execute("Python langage")
    assert result.success is True
    assert "Python" in result.content
    assert result.source == "web_agent"


@pytest.mark.asyncio
async def test_web_agent_empty_results():
    agent = WebAgent()
    with patch("httpx.AsyncClient", return_value=make_mock_client({"results": []})):
        result = await agent.execute("xzqwerty123456")
    assert result.success is False


@pytest.mark.asyncio
async def test_web_agent_timeout():
    agent = WebAgent()
    with patch("httpx.AsyncClient", return_value=make_mock_client(
        raise_exc=httpx.TimeoutException("timeout")
    )):
        result = await agent.execute("test timeout")
    assert result.success is False
    assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_web_agent_connect_error():
    agent = WebAgent()
    with patch("httpx.AsyncClient", return_value=make_mock_client(
        raise_exc=httpx.ConnectError("connection refused")
    )):
        result = await agent.execute("test connect")
    assert result.success is False
    assert "inaccessible" in result.error.lower()


@pytest.mark.asyncio
async def test_web_agent_http_error():
    agent = WebAgent()
    with patch("httpx.AsyncClient", return_value=make_mock_client(status_code=500)):
        result = await agent.execute("test http error")
    assert result.success is False
    assert "500" in result.error


@pytest.mark.asyncio
async def test_web_agent_latency_present(mock_searxng_response):
    agent = WebAgent()
    with patch("httpx.AsyncClient", return_value=make_mock_client(mock_searxng_response)):
        result = await agent.execute("test latency")
    assert result.latency_ms is not None
    assert isinstance(result.latency_ms, float)
