from __future__ import annotations

import logging
from typing import Any

from integrations.homeassistant.cache import MemoryCache
from integrations.homeassistant.client import HomeAssistantClient
from integrations.homeassistant.config import HomeAssistantConfig, load_config
from integrations.homeassistant.errors import HomeAssistantEntityNotFound
from integrations.homeassistant.helpers import detect_action, detect_domain, extract_number
from integrations.homeassistant.schemas import parse_state, parse_states
from integrations.homeassistant.search import EntitySearch
from integrations.homeassistant.types import HAMatch, HAState

logger = logging.getLogger("integrations.homeassistant")


class HomeAssistantService:
    def __init__(
        self,
        config: HomeAssistantConfig | None = None,
        client: HomeAssistantClient | None = None,
        cache: MemoryCache | None = None,
    ) -> None:
        self.config = config or load_config()
        self.client = client or HomeAssistantClient(self.config)
        self.cache = cache or MemoryCache(self.config.cache_ttl_seconds)

    async def health(self) -> dict[str, Any]:
        await self.client.get("/")
        return {"status": "healthy", "url": self.config.url}

    async def get_states(self, *, refresh: bool = False) -> list[HAState]:
        if not refresh:
            cached = self.cache.get("states")
            if isinstance(cached, list):
                logger.info("[HA] Cache hit states")
                return cached
        logger.info("[HA] Cache miss states")
        states = parse_states(await self.client.get("states"))
        self.cache.set("states", states)
        return states

    async def get_state(self, entity_id: str, *, refresh: bool = False) -> HAState:
        key = f"state:{entity_id}"
        if not refresh:
            cached = self.cache.get(key)
            if isinstance(cached, HAState):
                logger.info("[HA] Cache hit state entity_id=%s", entity_id)
                return cached
        state = parse_state(await self.client.get(f"states/{entity_id}"))
        self.cache.set(key, state)
        return state

    async def call_service(self, domain: str, service: str, data: dict[str, Any] | None = None) -> Any:
        logger.info("[HA] POST service domain=%s service=%s", domain, service)
        result = await self.client.post(f"services/{domain}/{service}", data or {})
        self.cache.invalidate()
        return result

    async def turn_on(self, entity_id: str) -> Any:
        return await self.callService(entity_id.split(".", 1)[0], "turn_on", {"entity_id": entity_id})

    async def turn_off(self, entity_id: str) -> Any:
        return await self.callService(entity_id.split(".", 1)[0], "turn_off", {"entity_id": entity_id})

    async def toggle(self, entity_id: str) -> Any:
        return await self.callService(entity_id.split(".", 1)[0], "toggle", {"entity_id": entity_id})

    async def callService(self, domain: str, service: str, data: dict[str, Any] | None = None) -> Any:
        return await self.call_service(domain, service, data)

    async def getStates(self) -> list[HAState]:
        return await self.get_states()

    async def getState(self, entity_id: str) -> HAState:
        return await self.get_state(entity_id)

    async def get_areas(self) -> list[dict[str, Any]]:
        payload = await self.client.get("config/area_registry")
        return payload if isinstance(payload, list) else []

    async def get_devices(self) -> list[dict[str, Any]]:
        payload = await self.client.get("config/device_registry")
        return payload if isinstance(payload, list) else []

    async def get_entities(self) -> list[dict[str, Any]]:
        payload = await self.client.get("config/entity_registry")
        return payload if isinstance(payload, list) else []

    async def getAreas(self) -> list[dict[str, Any]]:
        return await self.get_areas()

    async def getDevices(self) -> list[dict[str, Any]]:
        return await self.get_devices()

    async def getEntities(self) -> list[dict[str, Any]]:
        return await self.get_entities()

    async def search_entity(self, query: str, *, domain: str | None = None, limit: int = 5) -> list[HAMatch]:
        states = await self.get_states()
        matches = EntitySearch(states).search(query, domain=domain, limit=limit)
        if matches:
            logger.info("[HA] Entity found query=%r entity_id=%s score=%s", query, matches[0].entity_id, matches[0].score)
        return matches

    async def searchEntity(self, query: str, *, domain: str | None = None, limit: int = 5) -> list[HAMatch]:
        return await self.search_entity(query, domain=domain, limit=limit)

    async def get_history(self, entity_id: str | None = None) -> Any:
        suffix = f"?filter_entity_id={entity_id}" if entity_id else ""
        return await self.client.get(f"history/period{suffix}")

    async def getHistory(self, entity_id: str | None = None) -> Any:
        return await self.get_history(entity_id)

    async def execute_natural(self, text: str) -> dict[str, Any]:
        action = detect_action(text)
        domain = detect_domain(text)
        if action == "list":
            states = await self.get_states()
            filtered = [state for state in states if domain is None or state.domain == domain]
            return {
                "action": "list",
                "entities": [state.entity_id for state in filtered],
                "response": f"{len(filtered)} équipement(s) trouvé(s).",
            }

        matches = await self.search_entity(text, domain=domain, limit=3)
        if not matches:
            raise HomeAssistantEntityNotFound(text)
        match = matches[0]
        if action == "get_state":
            state = await self.get_state(match.entity_id)
            return {
                "action": "get_state",
                "entity_id": state.entity_id,
                "state": state.state,
                "response": f"{state.friendly_name} est actuellement {state.state}.",
            }

        service = _service_for_action(action, match.domain)
        data: dict[str, Any] = {"entity_id": match.entity_id}
        if service == "set_temperature":
            temperature = extract_number(text)
            if temperature is not None:
                data["temperature"] = temperature
        await self.call_service(match.domain, service, data)
        return {
            "action": action,
            "service": service,
            "entity_id": match.entity_id,
            "response": _response_for(action, match),
        }


def _service_for_action(action: str, domain: str) -> str:
    if action == "turn_off":
        return "turn_off"
    if action == "toggle":
        return "toggle"
    if action == "lock":
        return "lock"
    if action == "unlock":
        return "unlock"
    if action == "set" and domain == "climate":
        return "set_temperature"
    return "turn_on"


def _response_for(action: str, match: HAMatch) -> str:
    labels = {
        "turn_on": "activé",
        "turn_off": "désactivé",
        "toggle": "basculé",
        "lock": "verrouillé",
        "unlock": "déverrouillé",
        "set": "réglé",
    }
    return f"J'ai {labels.get(action, 'piloté')} {match.name}."


_SERVICE: HomeAssistantService | None = None


def get_homeassistant_service() -> HomeAssistantService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = HomeAssistantService()
    return _SERVICE
