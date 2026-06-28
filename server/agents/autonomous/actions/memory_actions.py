from __future__ import annotations


def semantic_memory_search(payload: dict):
    query = payload.get("query", "")

    return {
        "success": True,
        "type": "memory_search",
        "query": query,
        "result": f"Recherche mémoire simulée : {query}"
    }
