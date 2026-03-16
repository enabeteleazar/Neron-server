# neron_core/config.py
# Loader de configuration — neron.yaml (priorite) + .env (fallback)
# v2.1.0

import os
import logging
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

NERON_DIR = Path(os.getenv("NERON_DIR", Path(__file__).parent.parent))
YAML_PATH = NERON_DIR / "neron.yaml"


def _load_yaml() -> dict:
    if yaml is None:
        return {}
    if not YAML_PATH.exists():
        return {}
    with open(YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    logger.info(f"Config chargee depuis {YAML_PATH}")
    return data


def _get(cfg: dict, *keys: str, fallback_env: str = "", default: Any = None) -> Any:
    value = cfg
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            value = None
            break
    if value is not None and value != "":
        return value
    if fallback_env:
        env_value = os.getenv(fallback_env)
        if env_value is not None and env_value != "":
            return env_value
    return default


_cfg = _load_yaml()


class Config:
    # General
    VERSION        = _get(_cfg, "neron", "version",   fallback_env="NERON_VERSION",  default="2.1.0")
    LOG_LEVEL      = _get(_cfg, "neron", "log_level", fallback_env="LOG_LEVEL",       default="INFO")
    API_KEY        = _get(_cfg, "neron", "api_key",   fallback_env="NERON_API_KEY",   default="changez_moi")

    # Serveur
    SERVER_HOST    = _get(_cfg, "server", "host",     fallback_env="SERVER_HOST",     default="0.0.0.0")
    SERVER_PORT    = int(_get(_cfg, "server", "port", fallback_env="NERON_CORE_HTTP", default=8010))

    # LLM
    OLLAMA_MODEL    = _get(_cfg, "llm", "model",         fallback_env="OLLAMA_MODEL",    default="llama3.2:1b")
    SYSTEM_PROMPT   = _cfg.get("neron", {}).get("system_prompt", "Tu es Néron, un assistant IA personnel.")
    OLLAMA_HOST     = _get(_cfg, "llm", "host",          fallback_env="OLLAMA_HOST",     default="http://localhost:11434")
    LLM_TIMEOUT     = float(_get(_cfg, "llm", "timeout", fallback_env="LLM_TIMEOUT",     default=120))
    LLM_TEMPERATURE = float(_get(_cfg, "llm", "temperature",                             default=0.7))
    LLM_MAX_TOKENS  = int(_get(_cfg, "llm", "max_tokens",                                default=2048))

    # STT
    WHISPER_MODEL         = _get(_cfg, "stt", "model",          fallback_env="WHISPER_MODEL",         default="base")
    WHISPER_LANG          = _get(_cfg, "stt", "language",       fallback_env="WHISPER_LANGUAGE",      default="fr")
    STT_TIMEOUT           = int(_get(_cfg, "stt", "timeout",    fallback_env="STT_TIMEOUT",           default=60))
    AUDIO_MAX_MB          = int(_get(_cfg, "stt", "max_size_mb", fallback_env="AUDIO_MAX_SIZE_MB",    default=10))
    WHISPER_DOWNLOAD_ROOT = _get(_cfg, "stt", "download_root",  fallback_env="WHISPER_DOWNLOAD_ROOT", default=str(NERON_DIR / "data" / "models"))

    # TTS
    TTS_ENGINE    = _get(_cfg, "tts", "engine",   fallback_env="TTS_ENGINE",   default="pyttsx3")
    TTS_LANGUAGE  = _get(_cfg, "tts", "language", fallback_env="TTS_LANGUAGE", default="fr")
    TTS_RATE      = int(_get(_cfg, "tts", "rate",      fallback_env="TTS_RATE",      default=150))
    TTS_MAX_CHARS = int(_get(_cfg, "tts", "max_chars", fallback_env="TTS_MAX_CHARS", default=1000))

    # Telegram
    TELEGRAM_ENABLED      = str(_get(_cfg, "telegram", "enabled",         fallback_env="TELEGRAM_ENABLED",      default=False)).lower() == "true"
    TELEGRAM_BOT_TOKEN    = _get(_cfg, "telegram", "bot_token",           fallback_env="TELEGRAM_BOT_TOKEN",    default="")
    TELEGRAM_CHAT_ID      = _get(_cfg, "telegram", "chat_id",             fallback_env="TELEGRAM_CHAT_ID",      default="")
    TELEGRAM_NOTIFY_START = str(_get(_cfg, "telegram", "notify_on_start", default=True)).lower() != "false"

    # Watchdog
    WATCHDOG_ENABLED        = str(_get(_cfg, "watchdog", "enabled",            fallback_env="WATCHDOG_ENABLED",        default=False)).lower() == "true"
    WATCHDOG_INTERVAL       = int(_get(_cfg, "watchdog", "check_interval",     fallback_env="WATCHDOG_INTERVAL",       default=30))
    WATCHDOG_MAX_RETRIES    = int(_get(_cfg, "watchdog", "restart_max_retries",                                        default=3))
    WATCHDOG_ALERT_TG       = str(_get(_cfg, "watchdog", "alert_telegram",     default=True)).lower() != "false"
    WATCHDOG_BOT_TOKEN      = _get(_cfg, "watchdog", "bot_token",              fallback_env="WATCHDOG_BOT_TOKEN",      default="")
    WATCHDOG_CHAT_ID        = _get(_cfg, "watchdog", "chat_id",                fallback_env="WATCHDOG_CHAT_ID",        default="")
    WATCHDOG_CPU_ALERT      = float(_get(_cfg, "watchdog", "cpu_alert",        fallback_env="WATCHDOG_CPU_ALERT",      default=85))
    WATCHDOG_RAM_ALERT      = float(_get(_cfg, "watchdog", "ram_alert",        fallback_env="WATCHDOG_RAM_ALERT",      default=85))
    WATCHDOG_DISK_ALERT     = float(_get(_cfg, "watchdog", "disk_alert",       fallback_env="WATCHDOG_DISK_ALERT",     default=90))
    WATCHDOG_CPU_TEMP_ALERT = float(_get(_cfg, "watchdog", "cpu_temp_alert",   fallback_env="WATCHDOG_CPU_TEMP_ALERT", default=75))

    # Memoire
    MEMORY_DB_PATH   = NERON_DIR / _get(_cfg, "memory", "db_path",      default="data/memory.db")
    MEMORY_RETENTION = int(_get(_cfg, "memory", "retention_days",       default=30))

    # SearXNG
    SEARXNG_URL         = _get(_cfg, "searxng", "url",          fallback_env="SEARXNG_URL",          default="http://localhost:8080")
    SEARXNG_TIMEOUT     = float(_get(_cfg, "searxng", "timeout",    fallback_env="SEARXNG_TIMEOUT",    default=10.0))
    SEARXNG_MAX_RESULTS = int(_get(_cfg, "searxng", "max_results",  fallback_env="SEARXNG_MAX_RESULTS", default=5))

    # Home Assistant
    HA_ENABLED = str(_get(_cfg, "home_assistant", "enabled", fallback_env="HA_ENABLED", default=False)).lower() == "true"
    HA_URL     = _get(_cfg, "home_assistant", "url",   fallback_env="HA_URL",   default="http://homeassistant.local:8123")
    HA_TOKEN   = _get(_cfg, "home_assistant", "token", fallback_env="HA_TOKEN", default="")

    # System
    NERON_WATCHDOG_URL = _get(_cfg, "system", "watchdog_url", fallback_env="NERON_WATCHDOG_URL", default="http://localhost:8003")

    # Logs
    LOGS_DIR         = NERON_DIR / _get(_cfg, "logs", "dir",         default="logs")
    LOG_NERON        = _get(_cfg, "logs", "neron_log",               default="neron.log")
    LOG_WATCHDOG     = _get(_cfg, "logs", "watchdog_log",            default="watchdog.log")
    LOG_MAX_MB       = int(_get(_cfg, "logs", "max_size_mb",         default=10))
    LOG_BACKUP_COUNT = int(_get(_cfg, "logs", "backup_count",        default=5))


settings = Config()


def print_config():
    source = f"neron.yaml ({YAML_PATH})" if YAML_PATH.exists() else ".env / variables d'environnement"
    print(f"\n{'='*60}")
    print(f"  Neron AI - Configuration active")
    print(f"  Source : {source}")
    print(f"{'='*60}")
    print(f"  Version       : {settings.VERSION}")
    print(f"  Log level     : {settings.LOG_LEVEL}")
    print(f"  API port      : {settings.SERVER_PORT}")
    print(f"  LLM model     : {settings.OLLAMA_MODEL}")
    print(f"  LLM host      : {settings.OLLAMA_HOST}")
    print(f"  STT model     : {settings.WHISPER_MODEL} [{settings.WHISPER_LANG}]")
    print(f"  Whisper root  : {settings.WHISPER_DOWNLOAD_ROOT}")
    print(f"  TTS engine    : {settings.TTS_ENGINE}")
    print(f"  Telegram      : {'active' if settings.TELEGRAM_ENABLED else 'desactive'}")
    print(f"  Watchdog      : {'active' if settings.WATCHDOG_ENABLED else 'desactive'}")
    print(f"  SearXNG       : {settings.SEARXNG_URL}")
    print(f"  Watchdog URL  : {settings.NERON_WATCHDOG_URL}")
    print(f"  Memory DB     : {settings.MEMORY_DB_PATH}")
    print(f"  Logs dir      : {settings.LOGS_DIR}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print_config()
