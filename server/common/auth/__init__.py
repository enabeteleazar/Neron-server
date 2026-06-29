NERON_API_KEY_HEADER = "X-Neron-API-Key"


def api_key_headers(api_key: str) -> dict[str, str]:
    return {NERON_API_KEY_HEADER: api_key} if api_key else {}
