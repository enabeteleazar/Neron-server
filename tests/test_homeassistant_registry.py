from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from homeassistant_bridge import registry_runner
from server.common.registry.client import RegistryClient


def test_homeassistant_registry_payload_uses_common_sdk():
    with patch.object(registry_runner, "RegistryClient") as client_class:
        client = registry_runner.create_registry_client()

    assert client is client_class.return_value
    client_class.assert_called_once_with(
        service_name="homeassistant",
        version="0.1.0",
        host="localhost",
        port=8123,
        capabilities=["home_automation", "devices", "entities", "scenes"],
        metadata={},
    )


@pytest.mark.asyncio
async def test_sidecar_starts_and_stops_registry_client():
    client = Mock()
    client.start = AsyncMock()
    client.stop = AsyncMock()
    stop_event = asyncio.Event()

    async def start_and_stop() -> None:
        stop_event.set()

    client.start.side_effect = start_and_stop
    with patch.object(
        registry_runner,
        "create_registry_client",
        return_value=client,
    ):
        await registry_runner.run(stop_event)

    client.start.assert_awaited_once()
    client.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_sidecar_survives_core_unavailability():
    async def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Core unavailable", request=request)

    client = RegistryClient(
        service_name="homeassistant",
        version="0.1.0",
        host="localhost",
        port=8123,
        capabilities=["home_automation", "devices", "entities", "scenes"],
        metadata={},
        core_url="http://core.test",
        heartbeat_interval=0.01,
        initial_backoff=0.01,
        transport=httpx.MockTransport(unavailable),
    )
    stop_event = asyncio.Event()

    async def stop_later() -> None:
        await asyncio.sleep(0.015)
        stop_event.set()

    with patch.object(
        registry_runner,
        "create_registry_client",
        return_value=client,
    ):
        await asyncio.gather(
            registry_runner.run(stop_event),
            stop_later(),
        )

    assert client._closed is True
    assert client._registered is False
