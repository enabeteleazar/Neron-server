from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any

from server.common.config import env_float, env_int


@dataclass(frozen=True)
class RegistryService:
    service_name: str
    version: str
    host: str
    port: int
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.service_name.strip() or not self.host.strip():
            raise ValueError("service_name and host are required")
        if not 1 <= self.port <= 65_535:
            raise ValueError("port must be between 1 and 65535")

    def registration_payload(self) -> dict[str, Any]:
        return {
            "service_name": self.service_name,
            "host": self.host,
            "port": self.port,
            "version": self.version,
            "status": "healthy",
            "capabilities": list(self.capabilities),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RegistrySettings:
    core_url: str
    api_key: str
    heartbeat_interval: float
    timeout: float
    initial_backoff: float

    def __post_init__(self) -> None:
        if min(self.heartbeat_interval, self.timeout, self.initial_backoff) <= 0:
            raise ValueError("Registry timing values must be greater than zero")

    @classmethod
    def from_env(
        cls,
        heartbeat_interval: float = 30.0,
        timeout: float = 5.0,
        initial_backoff: float = 1.0,
    ) -> RegistrySettings:
        return cls(
            core_url=os.getenv(
                "NERON_CORE_URL",
                "http://localhost:8010",
            ).rstrip("/"),
            api_key=os.getenv("NERON_API_KEY", ""),
            heartbeat_interval=env_float(
                "NERON_HEARTBEAT_INTERVAL",
                heartbeat_interval,
            ),
            timeout=timeout,
            initial_backoff=initial_backoff,
        )


def service_from_env(
    *,
    service_name: str,
    version: str,
    host: str,
    port: int,
    capabilities: list[str],
    metadata: dict[str, Any],
) -> RegistryService:
    return RegistryService(
        service_name=service_name,
        version=version,
        host=os.getenv("NERON_SERVICE_HOST", host),
        port=env_int("NERON_SERVICE_PORT", port),
        capabilities=capabilities,
        metadata=metadata,
    )
