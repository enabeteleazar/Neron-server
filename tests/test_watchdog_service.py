from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from watchdog import app as watchdog_app
from watchdog.runtime import WatchdogRuntime, create_registry_client
from server.common.registry.client import RegistryClient


@pytest.mark.asyncio
async def test_watchdog_health_and_status_routes():
    runtime = Mock()
    runtime.uptime = 12.3456
    watchdog_app.app.state.watchdog_runtime = runtime

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=watchdog_app.app),
        base_url="http://watchdog.test",
    ) as client:
        health = await client.get("/health")
        status = await client.get("/status")

    assert health.status_code == 200
    assert health.json() == {"service": "watchdog", "status": "healthy"}
    assert status.status_code == 200
    assert status.json() == {
        "service": "watchdog",
        "status": "running",
        "uptime": 12.346,
    }


def test_watchdog_registry_client_uses_common_sdk_contract():
    with patch("watchdog.runtime.RegistryClient") as client_class:
        client = create_registry_client()

    assert client is client_class.return_value
    client_class.assert_called_once_with(
        service_name="watchdog",
        version="0.1.0",
        host="localhost",
        port=8050,
        capabilities=["monitoring", "alerts", "service_supervision"],
        metadata={},
    )


@pytest.mark.asyncio
async def test_watchdog_runtime_starts_registry_and_worker():
    registry = Mock()
    registry.start = AsyncMock()
    registry.stop = AsyncMock()

    with (
        patch("watchdog.runtime.create_registry_client", return_value=registry),
        patch("watchdog.runtime.start_watchdog", new_callable=AsyncMock) as start,
        patch("watchdog.runtime.stop_watchdog", new_callable=AsyncMock) as stop,
    ):
        runtime = WatchdogRuntime()
        await runtime.start()

        assert runtime.uptime >= 0
        start.assert_awaited_once()
        registry.start.assert_awaited_once()

        await runtime.stop()

    registry.stop.assert_awaited_once()
    stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_watchdog_lifespan_starts_and_stops_runtime():
    runtime = Mock()
    runtime.start = AsyncMock()
    runtime.stop = AsyncMock()
    runtime.started_at = time.monotonic()

    with patch.object(
        watchdog_app,
        "WatchdogRuntime",
        return_value=runtime,
    ):
        async with watchdog_app.lifespan(watchdog_app.app):
            runtime.start.assert_awaited_once()
            assert watchdog_app.app.state.watchdog_runtime is runtime

    runtime.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_watchdog_start_survives_registry_unavailability():
    async def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Core unavailable", request=request)

    registry = RegistryClient(
        service_name="watchdog",
        version="0.1.0",
        host="localhost",
        port=8050,
        capabilities=["monitoring", "alerts", "service_supervision"],
        metadata={},
        core_url="http://core.test",
        heartbeat_interval=0.01,
        initial_backoff=0.01,
        transport=httpx.MockTransport(unavailable),
    )
    with (
        patch("watchdog.runtime.create_registry_client", return_value=registry),
        patch("watchdog.runtime.start_watchdog", new_callable=AsyncMock),
        patch("watchdog.runtime.stop_watchdog", new_callable=AsyncMock),
    ):
        runtime = WatchdogRuntime()
        await runtime.start()
        await asyncio.sleep(0.01)
        assert registry._task is not None
        assert registry._registered is False
        await runtime.stop()
