from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from integrations.homeassistant.config import HomeAssistantConfig
from integrations.homeassistant.errors import (
    HomeAssistantApiError,
    HomeAssistantAuthError,
    HomeAssistantUnavailable,
)

logger = logging.getLogger("integrations.homeassistant")


class HomeAssistantClient:
    def __init__(
        self,
        config: HomeAssistantConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._transport = transport

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.token}",
            "Content-Type": "application/json",
        }

    async def get(self, path: str) -> Any:
        return await self._request("GET", path)

    async def post(self, path: str, payload: dict[str, Any]) -> Any:
        return await self._request("POST", path, json=payload)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.config.configured:
            raise HomeAssistantUnavailable("Home Assistant is not configured")
        url = f"{self.config.url}/api/{path.lstrip('/')}"
        last_error: Exception | None = None
        for attempt in range(self.config.retries + 1):
            try:
                logger.info("[HA] %s %s attempt=%s", method, path, attempt + 1)
                async with httpx.AsyncClient(
                    headers=self.headers,
                    timeout=self.config.timeout,
                    transport=self._transport,
                ) as client:
                    response = await client.request(method, url, **kwargs)
                if response.status_code in {401, 403}:
                    raise HomeAssistantAuthError("Home Assistant authentication failed")
                response.raise_for_status()
                if not response.content:
                    return {}
                return response.json()
            except HomeAssistantAuthError:
                raise
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
                last_error = exc
                logger.warning("[HA] network_error path=%s error=%s", path, type(exc).__name__)
            except httpx.HTTPStatusError as exc:
                raise HomeAssistantApiError(f"Home Assistant API error {exc.response.status_code}") from exc
            except ValueError as exc:
                raise HomeAssistantApiError("Home Assistant returned invalid JSON") from exc
            if attempt < self.config.retries:
                await asyncio.sleep(0.05 * (attempt + 1))
        raise HomeAssistantUnavailable("Home Assistant unavailable") from last_error
