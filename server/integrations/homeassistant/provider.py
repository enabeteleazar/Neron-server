from __future__ import annotations

from core.providers.models import ProviderRequest, ProviderResponse
from integrations.homeassistant.errors import HomeAssistantEntityNotFound, HomeAssistantError
from integrations.homeassistant.service import HomeAssistantService, get_homeassistant_service


class HomeAssistantProvider:
    name = "homeassistant"
    type = "homeassistant"
    capabilities = [
        "homeassistant.control",
        "homeassistant.state",
        "homeassistant.search",
        "homeassistant.history",
        "homeassistant.list",
    ]

    def __init__(self, service: HomeAssistantService | None = None) -> None:
        self.service = service or get_homeassistant_service()
        self._status = "unknown"

    @property
    def status(self) -> str:
        if not self.service.config.enabled:
            return "unavailable"
        if not self.service.config.configured:
            return "unavailable"
        return self._status

    async def health(self) -> ProviderResponse:
        try:
            result = await self.service.health()
            self._status = "healthy"
            return ProviderResponse(provider=self.name, action="health", status="healthy", result=result)
        except HomeAssistantError as exc:
            self._status = "unavailable"
            return ProviderResponse(provider=self.name, action="health", status="unavailable", error=exc.user_message)

    async def execute(self, request: ProviderRequest) -> ProviderResponse:
        try:
            result = await self._execute(request)
            self._status = "healthy"
            return ProviderResponse(
                provider=self.name,
                action=request.action,
                status="healthy",
                result=result,
                trace_id=request.trace_id,
            )
        except HomeAssistantEntityNotFound as exc:
            return ProviderResponse(
                provider=self.name,
                action=request.action,
                status="degraded",
                error=exc.user_message,
                trace_id=request.trace_id,
            )
        except HomeAssistantError as exc:
            self._status = "unavailable"
            return ProviderResponse(
                provider=self.name,
                action=request.action,
                status="unavailable",
                error=exc.user_message,
                trace_id=request.trace_id,
            )

    async def _execute(self, request: ProviderRequest):
        payload = request.payload
        if request.action in {"natural", "execute"}:
            return await self.service.execute_natural(str(payload.get("text") or payload.get("query") or ""))
        if request.action == "states":
            return [state.__dict__ for state in await self.service.get_states()]
        if request.action == "state":
            return (await self.service.get_state(str(payload["entity_id"]))).__dict__
        if request.action == "search":
            return [match.__dict__ for match in await self.service.search_entity(str(payload.get("query") or ""))]
        if request.action == "call_service":
            return await self.service.call_service(
                str(payload["domain"]),
                str(payload["service"]),
                dict(payload.get("data") or {}),
            )
        if request.action == "history":
            return await self.service.get_history(payload.get("entity_id"))
        raise HomeAssistantError(f"unsupported Home Assistant action: {request.action}")
