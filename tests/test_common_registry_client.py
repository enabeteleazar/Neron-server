from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import httpx
import pytest

from server.common.registry.client import RegistryClient
from server.common.registry.exceptions import (
    RegistryConnectionError,
    RegistryHTTPError,
    RegistryTimeoutError,
)


def _client(transport, **kwargs) -> RegistryClient:
    defaults = {
        "service_name": "test-service",
        "version": "1.0.0",
        "host": "localhost",
        "port": 9000,
        "capabilities": ["test"],
        "metadata": {"scope": "unit"},
        "core_url": "http://core.test",
        "api_key": "secret",
        "heartbeat_interval": 0.05,
        "initial_backoff": 0.01,
        "transport": transport,
        "trace_id_factory": lambda: "trace-test",
    }
    defaults.update(kwargs)
    return RegistryClient(**defaults)


@pytest.mark.asyncio
async def test_register_heartbeat_unregister_and_headers():
    requests: list[httpx.Request] = []

    async def core(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"status": "healthy"})

    client = _client(httpx.MockTransport(core))
    try:
        assert await client.register() is True
        assert await client.heartbeat() is True
        assert await client.unregister() is True
    finally:
        await client.stop()

    assert [request.method for request in requests] == ["POST", "POST", "DELETE"]
    assert [request.url.path for request in requests] == [
        "/registry/register",
        "/registry/heartbeat",
        "/registry/services/test-service",
    ]
    assert all(
        request.headers["X-Neron-API-Key"] == "secret"
        for request in requests
    )
    assert all(
        request.headers["X-Neron-Trace-Id"] == "trace-test"
        for request in requests
    )
    assert json.loads(requests[0].content)["capabilities"] == ["test"]


@pytest.mark.asyncio
async def test_http_timeout_and_connection_errors_are_typed():
    async def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client = _client(httpx.MockTransport(timeout))
    try:
        assert await client.register() is False
        assert isinstance(client.last_error, RegistryTimeoutError)
    finally:
        await client.stop()

    async def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unavailable", request=request)

    client = _client(httpx.MockTransport(unavailable))
    try:
        assert await client.register() is False
        assert isinstance(client.last_error, RegistryConnectionError)
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_http_error_is_preserved():
    async def core(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"detail": "invalid key"})

    client = _client(httpx.MockTransport(core))
    try:
        assert await client.register() is False
        assert isinstance(client.last_error, RegistryHTTPError)
        assert client.last_error.status_code == 403
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_progressive_backoff_resets_after_registration():
    attempts = 0
    delays: list[float] = []

    async def core(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        status = 503 if attempts < 3 else 200
        return httpx.Response(status)

    async def capture_sleep(delay: float) -> None:
        delays.append(delay)
        if len(delays) == 3:
            raise asyncio.CancelledError

    client = _client(httpx.MockTransport(core))
    try:
        with patch(
            "server.common.registry.client.asyncio.sleep",
            side_effect=capture_sleep,
        ):
            with pytest.raises(asyncio.CancelledError):
                await client._run()
    finally:
        await client.stop()

    assert delays == [0.01, 0.02, 0.05]
    assert client._registered is True


@pytest.mark.asyncio
async def test_reconnects_by_registering_after_heartbeat_failure():
    paths: list[str] = []
    heartbeat_failed = False

    async def core(request: httpx.Request) -> httpx.Response:
        nonlocal heartbeat_failed
        paths.append(request.url.path)
        if request.url.path == "/registry/heartbeat" and not heartbeat_failed:
            heartbeat_failed = True
            return httpx.Response(503)
        return httpx.Response(200)

    async def stop_after_reconnect(delay: float) -> None:
        if paths.count("/registry/register") == 2:
            raise asyncio.CancelledError

    client = _client(httpx.MockTransport(core))
    try:
        with patch(
            "server.common.registry.client.asyncio.sleep",
            side_effect=stop_after_reconnect,
        ):
            with pytest.raises(asyncio.CancelledError):
                await client._run()
    finally:
        await client.stop()

    assert paths[:3] == [
        "/registry/register",
        "/registry/heartbeat",
        "/registry/register",
    ]


@pytest.mark.asyncio
async def test_stop_cancels_worker_and_closes_transport():
    paths: list[str] = []

    async def core(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200)

    client = _client(httpx.MockTransport(core), heartbeat_interval=60)
    await client.start()
    for _ in range(10):
        if client._registered:
            break
        await asyncio.sleep(0)
    await client.stop()

    assert client._task is None
    assert client._closed is True
    assert paths == ["/registry/register"]
