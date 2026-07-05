from __future__ import annotations

import logging
import time
from pathlib import Path

from common.paths import NERON_IDENTITY_PATH

logger = logging.getLogger("neron.context")

NERON_CONTEXT_PATH = NERON_IDENTITY_PATH

_CACHE_TTL_SECONDS = 30.0
_cached_context: str | None = None
_cached_at: float = 0.0


def load_neron_context(force_reload: bool = False) -> str:
    """
    Charge le contexte opérationnel global depuis le document canonique NERON.md.

    Ce fichier sert de vérité opérationnelle compacte pour les agents,
    le raisonnement, le planner, le governor et les prompts système.
    """
    global _cached_context, _cached_at

    now = time.time()

    if (
        not force_reload
        and _cached_context is not None
        and now - _cached_at < _CACHE_TTL_SECONDS
    ):
        return _cached_context

    if not NERON_CONTEXT_PATH.exists():
        logger.warning("neron_context_missing path=%s", NERON_CONTEXT_PATH)
        _cached_context = ""
        _cached_at = now
        return ""

    try:
        content = NERON_CONTEXT_PATH.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.error("neron_context_load_failed path=%s error=%s", NERON_CONTEXT_PATH, exc)
        _cached_context = ""
        _cached_at = now
        return ""

    _cached_context = content
    _cached_at = now

    return content


def build_system_context(
    extra_context: str | None = None,
    *,
    include_neron_context: bool = True,
    force_reload: bool = False,
) -> str:
    """
    Construit un contexte système prêt à injecter dans un prompt LLM.

    - include_neron_context=True : ajoute NERON.md
    - extra_context : ajoute du contexte local spécifique à l'agent ou à la tâche
    """
    parts: list[str] = []

    if include_neron_context:
        neron_context = load_neron_context(force_reload=force_reload)
        if neron_context:
            parts.append("# GLOBAL NERON CONTEXT")
            parts.append(neron_context)

    if extra_context:
        parts.append("# LOCAL TASK CONTEXT")
        parts.append(extra_context.strip())

    return "\n\n---\n\n".join(parts).strip()


def has_neron_context(*, force_reload: bool = False) -> bool:
    """
    Indique si le contexte global NERON est disponible et non vide.

    S'appuie sur le même cache et la même logique de lecture que
    ``build_system_context`` pour éviter toute divergence.
    """
    return bool(load_neron_context(force_reload=force_reload).strip())


def get_neron_context_status() -> dict:
    """
    Retourne un état simple du contexte global.
    Utile pour debug/API/healthcheck.
    """
    exists = NERON_CONTEXT_PATH.exists()

    size_bytes = 0
    modified_at = None

    if exists:
        try:
            stat = NERON_CONTEXT_PATH.stat()
            size_bytes = stat.st_size
            modified_at = stat.st_mtime
        except OSError:
            pass

    return {
        "path": str(NERON_CONTEXT_PATH),
        "exists": exists,
        "size_bytes": size_bytes,
        "modified_at": modified_at,
        "cache_ttl_seconds": _CACHE_TTL_SECONDS,
        "cached": _cached_context is not None,
        "cached_at": _cached_at,
    }
