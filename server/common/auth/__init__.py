from __future__ import annotations

NERON_API_KEY_HEADER = "X-Neron-API-Key"


def api_key_headers(api_key: str) -> dict[str, str]:
    if not api_key:
        return {}
    return {NERON_API_KEY_HEADER: api_key}


__all__ = ["NERON_API_KEY_HEADER", "api_key_headers"]
