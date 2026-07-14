from __future__ import annotations

import os
from typing import Any

import httpx


MEMORY_URL = os.getenv(
    "NERON_MEMORY_URL",
    "http://127.0.1.4:8040",
).rstrip("/")


async def query_memory(
    query: str,
) -> dict[str, Any]:
    """
    Proxy vers le service neron-memory distant.
    """

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{MEMORY_URL}/memory/query",
            json={
                "query": query,
            },
        )

        response.raise_for_status()

        return response.json()


async def store_memory(
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Stockage mémoire distant.
    """

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{MEMORY_URL}/memory/store",
            json={
                "content": content,
                "metadata": metadata or {},
            },
        )

        response.raise_for_status()

        return response.json()


async def get_store() -> dict[str, str]:
    """
    Compatibilité temporaire.
    Le stockage est maintenant géré par server4-memory.
    """

    return {
        "backend": "remote",
        "url": MEMORY_URL,
    }
