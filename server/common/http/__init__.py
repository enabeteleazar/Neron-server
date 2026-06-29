"""HTTP primitives shared by NéronOS service clients."""

from __future__ import annotations

import httpx


def async_client(
    *,
    base_url: str,
    timeout: float,
    headers: dict[str, str],
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=timeout,
        headers=headers,
        transport=transport,
    )


__all__ = ["async_client"]
