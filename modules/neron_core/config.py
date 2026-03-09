# neron_core/config.py
# Loader de configuration — neron.yaml (priorité) + .env (fallback)
# v2.1.0

import os
import logging
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

# Répertoire de base : là où est installé Néron
NERON_DIR = Path(os.getenv("NERON_DIR", Path(__file__).parent.parent))
YAML_PATH = NERON_DIR / "neron.yaml"


def _load_yaml() -> dict:
    """Charge neron.yaml si disponible et si PyYAML est installé."""
    if yaml is None:
        logger.debug("PyYAML non installé — utilisation du fallback .env")
        return {}
    if not YAML_PATH.exists():
        logger.debug(f"neron.yaml introuvable à {YAML_PATH} — utilisation du fallback .env")
        return {}
    with open(YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    logger.info(f"Configuration chargée depuis {YAML_PATH}")
    return data


def _get(cfg: dict, *keys: str, fallback_env: str = "", default: Any = None) -> Any:
    """
    Cherche une valeur dans le YAML (chemin par clés),
    puis dans les variables d'environnement,
    puis retourne la valeur par défaut.
    """
    # 1. YAML
    value = cfg
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            value = None
            break
    if value is not None and value != "":
        return value

    # 2. Variable d'environnement (fallback .env)
    if fallback_env:
        env_value = os.getenv(fallback_env)
        if env_value is not None and env_value != "":
            return env_value

    # 3. Valeur par défaut
    return default


# ---------------------------------------------------------------------------
# Chargement unique au démarrage
# ---------------------------------------------------------------------------
_cfg = _load_yaml()


class Config:
    """Configuration centralisée Néron AI — lue depuis neron.yaml ou .env"""

    # --- Général ---
    VERSION:        str   = _get(_cfg, "neron", "version",   fallback_env="NERON_VERSION",  default="2.1.0")
    LOG_LEVEL:      str   = _get(_cfg, "neron", "log_level", fallback_env="LOG_LEVEL",       default="INFO")
    API_KEY:        str   = _get(_cfg, "neron", "api_key",   fallback_env="NERON_API_KEY",   default="changez_moi")

    # --- Serveur ---
    SERVER_HOST:    str   = _get(_cfg, "server", "host",     fallback_env="SERVER_HOST",     default="0.0.0.0")
    SERVER_PORT:    int   = int(_get(_cfg, "server", "port", fallback_env="NERON_CORE_HTTP", default=8000))

    # --- LLM ---
    OLLAMA_MODEL:   str   = _get(_cfg, "llm", "model",       fallback_env="OLLAMA_MODEL",    default="llama3.2:1b")
    OLLAMA_HOST:    str   = _get(_cfg, "llm", "host",        fallback_env="OLLAMA_HOST",     default="http://localhost:11434")
    LLM_TIMEOUT:    float = float(_get(_cfg, "llm", "timeout", fallback_env="LLM_TIMEOUT",   default=120))
    LLM_TEMPERATURE:float = float(_get(_cfg, "llm", "temperature",                           default=0.7))
    LLM_MAX_TOKENS: int   = int(_get(_cfg, "llm", "max_tokens",                              default=2048))

    # --- STT ---
    WHISPER_MODEL:  str   = _get(_cfg, "stt", "model",       fallback_env="WHISPER_MODEL",   default="base")
    WHISPER_LANG:   str   = _get(_cfg, "stt", "language",    fallback_env="WHISPER_LANGUAGE",default="fr")
    STT_TIMEOUT:    int   = int(_get(_cfg, "stt", "timeout", fallback_env="STT_TIMEOUT",     default=60))
    AUDIO_MAX_MB:   int   = int(_get(_cfg, "stt", "max_size_mb", fallback_env="AUDIO_MAX_SIZE_MB", default=10))

    # --- TTS ---
    TTS_ENGINE:     str   = _get(_cfg, "tts", "engine",      fallback_env="TTS_ENGINE",      default="pyttsx3")
    TTS_LANGUAGE:   str   = _get(_cfg, "tts", "language",    fallback_env="TTS_LANGUAGE",    default="fr")
    TTS_RATE:       int   = int(_get(_cfg, "tts", "rate",    fallback_env="TTS_RATE",        default=150))
    TTS_MAX_CHARS:  int   = int(_get(_cfg, "tts", "max_chars", fallback_env="TTS_MAX_CHARS", default=1000))

    # --- Telegram ---
    TELEGRAM_ENABLED:      bool = str(_get(_cfg, "telegram", "enabled", fallback_env="TELEGRAM_ENABLED", default=False)).lower() == "true"
    TELEGRAM_BOT_TOKEN:    str  = _get(_cfg, "telegram", "bot_token",   fallback_env="TELEGRAM_BOT_TOKEN", default="")
    TELEGRAM_CHAT_ID:      str  = _get(_cfg, "telegram", "chat_id",     fallback_env="TELEGRAM_CHAT_ID",   default="")
    TELEGRAM_NOTIFY_START: bool = str(_get(_cfg, "telegram", "notify_on_start", default=True)).lower() != "false"

    # --- Watchdog ---
    WATCHDOG_ENABLED:      bool = str(_get(_cfg, "watchdog", "enabled", fallback_env="WATCHDOG_ENABLED", default=False)).lower() == "true"
    WATCHDOG_INTERVAL:     int  = int(_get(_cfg, "watchdog", "check_interval",     default=30))
    WATCHDOG_MAX_RETRIES:  int  = int(_get(_cfg, "watchdog", "restart_max_retries",default=3))
    WATCHDOG_ALERT_TG:     bool = str(_get(_cfg, "watchdog", "alert_telegram",     default=True)).lower() != "false"

    # --- Mémoire ---
    MEMORY_DB_PATH:     Path = NERON_DIR / _get(_cfg, "memory", "db_path", default="data/memory.db")
    MEMORY_RETENTION:   int  = int(_get(_cfg, "memory", "retention_days", default=30))

    # --- Logs ---
    LOGS_DIR:       Path  = NERON_DIR / _get(_cfg, "logs", "dir",          default="logs")
    LOG_NERON:      str   = _get(_cfg, "logs", "neron_log",                 default="neron.log")
    LOG_WATCHDOG:   str   = _get(_cfg, "logs", "watchdog_log",              default="watchdog.log")
    LOG_MAX_MB:     int   = int(_get(_cfg, "logs", "max_size_mb",           default=10))
    LOG_BACKUP_COUNT:int  = int(_get(_cfg, "logs", "backup_count",          default=5))


# Instance globale importable partout
settings = Config()


# ---------------------------------------------------------------------------
# Utilitaire : afficher la config active (pour `neron env` / `neron doctor`)
# ---------------------------------------------------------------------------
def print_config():
    source = f"neron.yaml ({YAML_PATH})" if YAML_PATH.exists() else ".env / variables d'environnement"
    print(f"\n{'='*60}")
    print(f"  Néron AI — Configuration active")
    print(f"  Source : {source}")
    print(f"{'='*60}")
    print(f"  Version       : {settings.VERSION}")
    print(f"  Log level     : {settings.LOG_LEVEL}")
    print(f"  API port      : {settings.SERVER_PORT}")
    print(f"  LLM model     : {settings.OLLAMA_MODEL}")
    print(f"  LLM host      : {settings.OLLAMA_HOST}")
    print(f"  STT model     : {settings.WHISPER_MODEL} [{settings.WHISPER_LANG}]")
    print(f"  TTS engine    : {settings.TTS_ENGINE}")
    print(f"  Telegram      : {'activé' if settings.TELEGRAM_ENABLED else 'désactivé'}")
    print(f"  Watchdog      : {'activé' if settings.WATCHDOG_ENABLED else 'désactivé'}")
    print(f"  Memory DB     : {settings.MEMORY_DB_PATH}")
    print(f"  Logs dir      : {settings.LOGS_DIR}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print_config()
