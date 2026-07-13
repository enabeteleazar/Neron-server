from __future__ import annotations

from typing import Any

from integrations.homeassistant.types import HAState


def parse_state(payload: dict[str, Any]) -> HAState:
    entity_id = str(payload.get("entity_id") or "")
    if not entity_id or "." not in entity_id:
        raise ValueError("invalid Home Assistant state payload")
    attributes = payload.get("attributes") if isinstance(payload.get("attributes"), dict) else {}
    return HAState(
        entity_id=entity_id,
        state=str(payload.get("state") or "unknown"),
        attributes=dict(attributes),
        last_changed=payload.get("last_changed"),
        last_updated=payload.get("last_updated"),
    )


def parse_states(payload: object) -> list[HAState]:
    if not isinstance(payload, list):
        raise ValueError("Home Assistant states response must be a list")
    return [parse_state(item) for item in payload if isinstance(item, dict)]
