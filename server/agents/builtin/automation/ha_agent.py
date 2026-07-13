from __future__ import annotations

import asyncio
from typing import Any

from agents.builtin.base_agent import AgentResult, BaseAgent
from integrations.homeassistant.errors import HomeAssistantEntityNotFound, HomeAssistantError
from integrations.homeassistant.service import HomeAssistantService, get_homeassistant_service


class HAAgent(BaseAgent):
    """Legacy agent facade over the native Home Assistant integration."""

    def __init__(self, service: HomeAssistantService | None = None) -> None:
        super().__init__(name="ha_agent")
        self.service = service or get_homeassistant_service()
        self._refresh_task: asyncio.Task | None = None

    async def on_start(self) -> None:
        if not self.service.config.enabled:
            self.logger.warning("HA désactivé (HA_ENABLED=false)")
            return
        if not self.service.config.configured:
            self.logger.warning("HA_URL/HA_TOKEN manquants")
            return
        try:
            states = await self.service.get_states(refresh=True)
            self.logger.info("[HA] states chargés : %d entités", len(states))
        except HomeAssistantError as exc:
            self.logger.warning("[HA] startup unavailable: %s", exc.user_message)
            return
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def on_stop(self) -> None:
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(self.service.config.refresh_interval_seconds)
            await self.reload()

    async def reload(self) -> int:
        try:
            states = await self.service.get_states(refresh=True)
            self.logger.info("[HA] reload OK entities=%d", len(states))
            return len(states)
        except HomeAssistantError as exc:
            self.logger.warning("[HA] reload failed: %s", exc.user_message)
            cached = await self._cached_state_count()
            return cached

    async def execute(self, query: str, **kwargs: Any) -> AgentResult:
        del kwargs
        start = self._timer()
        try:
            result = await self.service.execute_natural(query)
            return self._success(
                content=str(result.get("response") or "Action Home Assistant exécutée."),
                metadata=result,
                latency_ms=self._elapsed_ms(start),
                confidence="high",
            )
        except HomeAssistantEntityNotFound as exc:
            return self._failure(exc.user_message, latency_ms=self._elapsed_ms(start))
        except HomeAssistantError as exc:
            return self._failure(exc.user_message, latency_ms=self._elapsed_ms(start))
        except Exception as exc:
            self.logger.exception("[HA] unexpected_error")
            return self._failure(f"Erreur Home Assistant : {exc}", latency_ms=self._elapsed_ms(start))

    async def get_states(self) -> list[dict]:
        try:
            return [state.__dict__ for state in await self.service.get_states()]
        except HomeAssistantError:
            return []

    async def check_connection(self) -> bool:
        try:
            await self.service.health()
            return True
        except HomeAssistantError:
            return False

    async def _cached_state_count(self) -> int:
        cached = self.service.cache.get("states")
        return len(cached) if isinstance(cached, list) else 0
