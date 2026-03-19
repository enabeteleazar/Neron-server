"""
personality/__init__.py — API publique du module Neron Personality

Expose :
- build_system_prompt(user_context)   : prompt prêt à envoyer au LLM
- update_from_feedback(feedback)      : mise à jour via analyse d'intention
- force_update(section, field, value) : mise à jour directe programmatique
- get_current_state()                 : état complet de la persona active
- get_history(limit)                  : historique des changements d'état

Corrections v5 :
- _safe_json_load importé depuis loader (plus de duplication)
- get_history utilise _safe_json_load centralisé
"""

import logging

from .engine  import build_system_prompt
from .updater import update_from_feedback, force_update
from .loader  import load_persona, _init_db, _safe_json_load  # _safe_json_load centralisé

logger = logging.getLogger(__name__)

__all__ = [
    "build_system_prompt",
    "update_from_feedback",
    "force_update",
    "get_current_state",
    "get_history",
]


def get_current_state() -> dict:
    """
    Retourne la configuration active complète de la persona.

    Inclut :
    - Tous les champs de persona.yaml (base immuable)
    - L'état dynamique SQLite fusionné (verbosity, tone, mood, energy_level, learning)
    - Les DEFAULTS pour tout champ manquant

    Usage :
        from core.personality import get_current_state
        state = get_current_state()
        print(state["mood"])           # ex: "focus"
        print(state["communication"])  # ex: {"tone": "direct", "verbosity": "low"}
        print(state["learning"])       # ex: {"enabled": True}
    """
    try:
        return load_persona()
    except Exception as e:
        logger.error(f"[PERSONALITY] get_current_state échoué : {e}")
        return {
            "error":        str(e),
            "status":       "unavailable",
            "name":         "Neron",
            "mood":         "neutre",
            "energy_level": "normal",
        }


def get_history(limit: int = 20) -> list[dict]:
    """
    Retourne les dernières entrées de l'historique des changements d'état.
    Utilise _init_db() pour garantir que les tables existent.
    Désérialise via _safe_json_load importé depuis loader (source unique).

    Args:
        limit: nombre maximum d'entrées à retourner (défaut : 20)

    Returns:
        Liste de dicts : id, timestamp, field, old_value, new_value, reason

    Usage :
        from core.personality import get_history
        for entry in get_history(10):
            print(f"{entry['timestamp']} | {entry['field']}: "
                  f"{entry['old_value']} → {entry['new_value']}")
    """
    conn = None
    try:
        conn = _init_db()
        cursor = conn.execute(
            """SELECT id, timestamp, field, old_value, new_value, reason
               FROM persona_history
               ORDER BY id DESC
               LIMIT ?""",
            (limit,)
        )
        rows = cursor.fetchall()

        return [
            {
                "id":        id_,
                "timestamp": ts,
                "field":     field,
                "old_value": _safe_json_load(old_val),
                "new_value": _safe_json_load(new_val),
                "reason":    reason or "",
            }
            for id_, ts, field, old_val, new_val, reason in rows
        ]

    except Exception as e:
        logger.error(f"[PERSONALITY] get_history échoué : {e}")
        return [{"error": str(e)}]

    finally:
        if conn is not None:
            conn.close()
