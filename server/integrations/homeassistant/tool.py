from __future__ import annotations

from typing import Any

from integrations.homeassistant.errors import HomeAssistantEntityNotFound, HomeAssistantError
from integrations.homeassistant.service import get_homeassistant_service
from tools.models import ToolResult, ToolSpec


HOMEASSISTANT_TOOL_SLUG = "homeassistant"


def tool_spec() -> ToolSpec:
    return ToolSpec(
        name="homeassistant",
        slug=HOMEASSISTANT_TOOL_SLUG,
        description=(
            "Permet à Néron d'interagir avec Home Assistant: lecture d'états, "
            "pilotage des équipements, recherche d'entités et exécution de services."
        ),
        inputs={
            "action": "natural|states|state|search|call_service|history",
            "text": "Commande naturelle optionnelle",
            "entity_id": "Identifiant Home Assistant optionnel",
            "domain": "Domaine Home Assistant optionnel",
            "service": "Service Home Assistant optionnel",
            "data": "Payload service optionnel",
        },
        outputs={"response": "Réponse naturelle", "data": "Résultat structuré"},
        safety={"allow_system_commands": False, "requires_network": True},
        source="builtin",
        metadata={
            "aliases": ["domotique", "home assistant", "lumiere", "chauffage", "volets"],
        },
    )


async def execute(payload: dict[str, Any] | None = None) -> ToolResult:
    payload = dict(payload or {})
    action = str(payload.get("action") or "natural")
    service = get_homeassistant_service()
    try:
        if action == "natural":
            result = await service.execute_natural(str(payload.get("text") or payload.get("query") or ""))
        elif action == "states":
            result = {"states": [state.__dict__ for state in await service.get_states()]}
        elif action == "state":
            result = (await service.get_state(str(payload["entity_id"]))).__dict__
        elif action == "search":
            result = {"matches": [match.__dict__ for match in await service.search_entity(str(payload.get("query") or ""))]}
        elif action == "call_service":
            result = await service.call_service(
                str(payload["domain"]),
                str(payload["service"]),
                dict(payload.get("data") or {}),
            )
        elif action == "history":
            result = await service.get_history(payload.get("entity_id"))
        else:
            return ToolResult(ok=False, error=f"unsupported_action:{action}")
        return ToolResult(ok=True, response=str(result.get("response") or "Action Home Assistant exécutée."), data=dict(result))
    except HomeAssistantEntityNotFound as exc:
        return ToolResult(ok=False, response=exc.user_message, error=exc.user_message)
    except HomeAssistantError as exc:
        return ToolResult(ok=False, response=exc.user_message, error=exc.user_message)
