from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SECRETS_PATHS = (
    ROOT / "secrets.env",
    ROOT / "secret.env",
    Path("/etc/neron/secrets.env"),
)


@dataclass(frozen=True)
class HomeAssistantConfig:
    enabled: bool = False
    url: str = ""
    token: str = ""
    timeout: float = 10.0
    retries: int = 2
    cache_ttl_seconds: float = 30.0
    refresh_interval_seconds: float = 300.0

    @property
    def configured(self) -> bool:
        return bool(self.url and self.token)


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _secrets() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in DEFAULT_SECRETS_PATHS:
        merged.update(_parse_env_file(path))
    return merged


def _project_config() -> dict[str, Any]:
    path = ROOT / "neron.yaml"
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_config() -> HomeAssistantConfig:
    secrets = _secrets()
    project = _project_config()
    ha = project.get("home_assistant") or project.get("homeassistant") or {}
    if not isinstance(ha, dict):
        ha = {}

    token_env = str(ha.get("token_env") or "HA_TOKEN")
    token = os.getenv("HA_TOKEN") or os.getenv(token_env) or secrets.get("HA_TOKEN") or secrets.get(token_env) or ""
    url = os.getenv("HA_URL") or secrets.get("HA_URL") or str(ha.get("url") or "")

    return HomeAssistantConfig(
        enabled=_bool(os.getenv("HA_ENABLED"), _bool(ha.get("enabled"), False)),
        url=url.rstrip("/"),
        token=token,
        timeout=_float(os.getenv("HA_TIMEOUT") or ha.get("timeout"), 10.0),
        retries=_int(os.getenv("HA_RETRIES") or ha.get("retries"), 2),
        cache_ttl_seconds=_float(os.getenv("HA_CACHE_TTL_SECONDS") or ha.get("cache_ttl_seconds"), 30.0),
        refresh_interval_seconds=_float(
            os.getenv("HA_REFRESH_INTERVAL_SECONDS") or ha.get("refresh_interval_seconds") or ha.get("sync_interval"),
            300.0,
        ),
    )
