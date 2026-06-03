"""Agent déterministe: searchx (wrapper pour searxng / web search)
Reconnecte l'API existante via server/core modules.
"""

def search(query: str, limit: int = 5):
    # lazy import pour éviter dépendances cycles
    try:
        from core.modules.searxng import search as _search
        return _search(query, limit=limit)
    except Exception:
        return {"results": [], "error": "search backend unavailable"}
