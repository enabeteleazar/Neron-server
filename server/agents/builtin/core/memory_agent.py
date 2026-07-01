"""Compatibility memory agent backed exclusively by Oblivia over A2A."""

from __future__ import annotations

from typing import Any

from core.providers.models import ProviderRequest, ProviderResponse
from core.providers.registry import provider_registry
from modules.events.event import Event
from modules.events.event_bus import event_bus
from modules.events.event_types import MEMORY_UPDATED


def init_db() -> None:
    """Deprecated compatibility hook; Oblivia initializes its own storage."""


class MemoryAgent:
    async def _execute(
        self,
        action: str,
        payload: dict[str, Any],
    ) -> ProviderResponse:
        providers = provider_registry.by_type("memory")
        if not providers:
            return ProviderResponse(
                provider="oblivia",
                action=action,
                status="unavailable",
                error="memory provider unavailable",
            )
        return await provider_registry.execute_via_a2a(
            providers[0].name,
            ProviderRequest(action=action, payload=payload),
        )

    async def reload(self) -> bool:
        response = await self._execute("health", {})
        return response.error is None

    async def retrieve(self, limit: int = 3) -> list[dict[str, Any]]:
        response = await self._execute("recent", {"limit": limit})
        return self._entries(response.result)

    async def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        response = await self._execute(
            "search",
            {"query": query, "limit": limit},
        )
        return self._entries(response.result)

    async def get_context(self, query: str, limit: int = 3) -> str | None:
        entries = await self.search(query, limit=limit)
        if not entries:
            return None
        return "Mémoire pertinente :\n" + "\n".join(
            f"- {entry['content']}" for entry in entries
        )

    async def save(
        self,
        input_text: str,
        response: str,
        metadata: dict | None = None,
    ) -> str | None:
        saved = await self._execute(
            "remember",
            {
                "content": f"Utilisateur: {input_text}\nRéponse: {response}",
                "category": "runtime",
                "metadata": {
                    **(metadata or {}),
                    "input": input_text,
                    "response": response,
                    "memory_type": "episodic",
                },
            },
        )
        if saved.error or not isinstance(saved.result, dict):
            return None
        record_id = str(saved.result.get("id") or "")
        await event_bus.publish(Event(
            type=MEMORY_UPDATED,
            source="memory_agent",
            payload={
                "action": "remember",
                "record_id": record_id,
                "metadata": dict(metadata or {}),
                "provider": saved.provider,
                "transport": "a2a",
            },
        ))
        return record_id or None

    async def cleanup(self, days: int = 30) -> int:
        response = await self._execute("cleanup", {"days": days})
        if response.error or not isinstance(response.result, dict):
            return 0
        return int(response.result.get("deleted") or 0)

    async def count(self) -> int:
        response = await self._execute("status", {})
        if response.error or not isinstance(response.result, dict):
            return 0
        return int((response.result.get("sqlite") or {}).get("records") or 0)

    @staticmethod
    def _entries(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        entries = []
        for item in value:
            record = item.get("record") if isinstance(item, dict) else None
            if isinstance(record, dict):
                entries.append({
                    "id": record.get("id"),
                    "content": record.get("content") or "",
                    "category": record.get("category"),
                    "metadata": record.get("metadata") or {},
                    "backend": item.get("backend"),
                })
        return entries
