class RegistryClientError(Exception):
    """Base Registry client error."""


class RegistryTimeoutError(RegistryClientError):
    """Core Registry request timed out."""


class RegistryConnectionError(RegistryClientError):
    """Core Registry could not be reached."""


class RegistryHTTPError(RegistryClientError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
