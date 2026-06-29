from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
from typing import Any, Callable

import httpx

from server.common.auth import api_key_headers
from server.common.http import async_client
from server.common.logging import get_service_logger
from server.common.registry.exceptions import (
    RegistryClientError,
    RegistryConnectionError,
    RegistryHTTPError,
    RegistryTimeoutError,
)
from server.common.registry.models import RegistrySettings, service_from_env
from server.common.tracing import new_trace_id


class RegistryClient:
    def __init__(
        self,
        *,
        service_name: str,
        version: str,
        host: str,
        port: int,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        core_url: str | None = None,
        api_key: str | None = None,
        heartbeat_interval: float | None = None,
        timeout: float = 5.0,
        initial_backoff: float = 1.0,
        transport: httpx.AsyncBaseTransport | None = None,
        logger: logging.Logger | None = None,
        trace_id_factory: Callable[[], str] = new_trace_id,
    ) -> None:
        env = RegistrySettings.from_env(
            heartbeat_interval or 30.0,
            timeout,
            initial_backoff,
        )
        self.settings = RegistrySettings(
            core_url=(core_url or env.core_url).rstrip("/"),
            api_key=env.api_key if api_key is None else api_key,
            heartbeat_interval=(
                env.heartbeat_interval
                if heartbeat_interval is None
                else heartbeat_interval
            ),
            timeout=timeout,
            initial_backoff=initial_backoff,
        )
        self.service = service_from_env(
            service_name=service_name,
            version=version,
            host=host,
            port=port,
            capabilities=list(capabilities or []),
            metadata=dict(metadata or {}),
        )
        self._logger = logger or get_service_logger(
            f"registry.{self.service.service_name}"
        )
        self._trace_id_factory = trace_id_factory
        self._client = async_client(
            base_url=self.settings.core_url,
            timeout=self.settings.timeout,
            headers=api_key_headers(self.settings.api_key),
            transport=transport,
        )
        self._task: asyncio.Task[None] | None = None
        self._registered = False
        self._closed = False
        self.last_error: RegistryClientError | None = None

    async def start(self) -> None:
        if self._closed:
            raise RuntimeError("RegistryClient is closed")
        if self._task is None:
            self._task = asyncio.create_task(
                self._run(),
                name=f"{self.service.service_name}-registry",
            )

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if not self._closed:
            await self._client.aclose()
            self._closed = True

    async def register(self) -> bool:
        success = await self._send(
            "POST",
            "/registry/register",
            self.service.registration_payload(),
            "registration",
        )
        if success:
            self._registered = True
            self._logger.info(
                "Registered %s with Core Registry",
                self.service.service_name,
            )
        return success

    async def heartbeat(self) -> bool:
        success = await self._send(
            "POST",
            "/registry/heartbeat",
            {
                "service_name": self.service.service_name,
                "status": "healthy",
            },
            "heartbeat",
        )
        if not success:
            self._registered = False
        return success

    async def unregister(self) -> bool:
        success = await self._send(
            "DELETE",
            f"/registry/services/{self.service.service_name}",
            None,
            "unregistration",
        )
        if success:
            self._registered = False
        return success

    async def _run(self) -> None:
        backoff = self.settings.initial_backoff
        while True:
            success = (
                await self.heartbeat()
                if self._registered
                else await self.register()
            )
            if success:
                backoff = self.settings.initial_backoff
                delay = self.settings.heartbeat_interval
            else:
                delay = min(backoff, self.settings.heartbeat_interval)
                backoff = min(backoff * 2, self.settings.heartbeat_interval)
            await asyncio.sleep(delay)

    async def _send(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        operation: str,
    ) -> bool:
        try:
            response = await self._client.request(
                method,
                path,
                json=payload,
                headers={"X-Neron-Trace-Id": self._trace_id_factory()},
            )
            if response.is_error:
                raise RegistryHTTPError(
                    response.status_code,
                    f"Core Registry returned HTTP {response.status_code}",
                )
        except httpx.TimeoutException as exc:
            self.last_error = RegistryTimeoutError(str(exc))
        except httpx.RequestError as exc:
            self.last_error = RegistryConnectionError(str(exc))
        except RegistryClientError as exc:
            self.last_error = exc
        else:
            self.last_error = None
            return True
        self._logger.warning(
            "Core Registry %s failed for %s: %s",
            operation,
            self.service.service_name,
            self.last_error,
        )
        return False
