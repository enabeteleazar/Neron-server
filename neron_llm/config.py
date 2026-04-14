"""Configuration loader with memory cache for neron_llm.

Reads from /etc/neron/server/neron.yaml once and caches in memory.
Supports both 'routing' (v1.0) and 'model_map' (legacy) keys.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml

logger = logging.getLogger("neron_llm.config")

CONFIG_PATH = Path("/etc/neron/server/neron.yaml")

# Keys that are NOT model mappings (e.g. timeout) — filtered out of routing
_ROUTING_META_KEYS = {"timeout", "default_provider"}


def load_config() -> dict:
    """Load and cache the full YAML configuration."""
    return _load_config_cached()


@lru_cache(maxsize=1)
def _load_config_cached() -> dict:
    """Load YAML config once and cache in memory."""
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f) or {}
        logger.info("Configuration loaded from %s", CONFIG_PATH)
        return config
    except FileNotFoundError:
        logger.error("Config file not found: %s", CONFIG_PATH)
        return {}
    except yaml.YAMLError as e:
        logger.error("YAML parse error: %s", e)
        return {}


def get_llm_config() -> dict:
    """Get the 'llm' section of the config."""
    return load_config().get("llm", {})


def get_routing_config() -> dict:
    """Get the routing section. Prefers 'routing' key, falls back to 'model_map'."""
    config = load_config()
    routing = config.get("routing", {})
    if not routing:
        routing = config.get("model_map", {})
    # Filter out meta keys (timeout, default_provider, etc.)
    return {k: v for k, v in routing.items() if k not in _ROUTING_META_KEYS}


def reload_config() -> dict:
    """Force reload the configuration (clears LRU cache)."""
    _load_config_cached.cache_clear()
    new_config = load_config()
    logger.info("Configuration reloaded from %s", CONFIG_PATH)
    return new_config