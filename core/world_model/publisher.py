# core/world_model/publisher.py
# Néron v2 — Publication légère dans le World Model (IPC via fichier JSON)
#
# Usage depuis n'importe quel agent/process :
#   from core.world_model.publisher import publish
#   publish("llm_agent", {"status": "online", "latency_ms": 320})

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from core.config import settings

logger = logging.getLogger("world_model.publisher")

# Fichier JSON partagé entre tous les process
_WM_DIR        = settings.LOGS_DIR.parent / "data" / "world_model"
_AGENTS_STATE  = _WM_DIR / "agents_state.json"
_LOCK_SUFFIX   = ".lock"


def _atomic_read() -> dict:
    """Lit le fichier d'état agents de façon sûre."""
    try:
        if _AGENTS_STATE.exists():
            return json.loads(_AGENTS_STATE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("publisher._atomic_read error : %s", e)
    return {}


def _atomic_write(data: dict) -> None:
    """Écrit le fichier d'état agents de façon atomique (tmp → replace)."""
    _WM_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _AGENTS_STATE.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        tmp.replace(_AGENTS_STATE)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        logger.error("publisher._atomic_write error : %s", e)
        raise


def publish(agent_name: str, data: dict) -> None:
    """
    Publie l'état d'un agent dans le World Model partagé.

    Args:
        agent_name : identifiant de l'agent (ex: "llm_agent", "watchdog")
        data       : dict de métriques à publier (status, latency, etc.)

    Ajoute automatiquement un timestamp "ts" si absent.
    """
    if "ts" not in data:
        data["ts"] = round(time.time(), 2)

    try:
        state = _atomic_read()
        state[agent_name] = data
        _atomic_write(state)
    except Exception as e:
        logger.error("publish(%s) error : %s", agent_name, e)


def read_all() -> dict:
    """
    Retourne l'état de tous les agents publiés.
    Filtre les agents dont le dernier heartbeat est > 5 minutes.
    """
    state   = _atomic_read()
    now     = time.time()
    timeout = 300  # 5 minutes

    result = {}
    for name, data in state.items():
        ts = data.get("ts", 0)
        if now - ts < timeout:
            result[name] = data
        else:
            result[name] = {**data, "status": "stale"}

    return result


def read_agent(agent_name: str) -> dict | None:
    """Retourne l'état d'un agent spécifique."""
    return _atomic_read().get(agent_name)
