AUTHORIZATION_HEADER = "Authorization"


def api_key_headers(api_key: str) -> dict[str, str]:
    return {AUTHORIZATION_HEADER: f"Bearer {api_key}"} if api_key else {}
