from __future__ import annotations


class RegistryClientError(Exception):
    """Base error raised by Registry transport operations."""


class RegistryTimeoutError(RegistryClientError):
    """The Core Registry did not answer before the configured timeout."""


class RegistryConnectionError(RegistryClientError):
    """The Core Registry could not be reached."""


class RegistryHTTPError(RegistryClientError):
    """The Core Registry returned a non-success HTTP status."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
