"""
updater.py — Mise à jour de l'état dynamique de Neron

Corrections v7 :
- ALLOWED_VALUES étendu aux booléens (proactive, suggest_improvements, enabled)
  → toute valeur non-booléenne est refusée avec warning
- update_from_feedback retourne status='no_change' (et non 'updated')
  quand tous les changements détectés sont des no-ops ou des refus
"""

import json
import logging
import functools
from datetime import datetime, timezone
from typing import Any

from .loader import _init_db, _read_field, _load_yaml_base, _get_protected_fields

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Matrice d'intentions
# ---------------------------------------------------------------------------
INTENT_MATRIX = [
    # --- Verbosité ---
    (["trop long", "trop verbeux", "trop bavard", "raccourcis", "sois bref"],
     "communication", "verbosity", "low"),
    (["plus de détail", "développe", "explique mieux", "j'ai pas compris", "trop court"],
     "communication", "verbosity", "high"),
    (["c'est bien", "parfait", "niveau ok", "longueur ok"],
     "communication", "verbosity", "medium"),

    # --- Ton ---
    (["sois direct", "va droit au but", "sans détour", "sans blabla"],
     "communication", "tone", "direct"),
    (["plus doux", "sois plus sympa", "moins froid", "plus chaleureux"],
     "communication", "tone", "bienveillant"),
    (["redeviens technique", "mode technique", "sois technique"],
     "communication", "tone", "technique"),

    # --- Proactivité ---
    (["arrête de proposer", "moins de suggestions", "pas de suggestions"],
     "behavior", "proactive", False),
    (["sois proactif", "propose plus", "plus de suggestions", "anticipe"],
     "behavior", "proactive", True),

    # --- Apprentissage ---
    (["arrête d'apprendre", "désactive l'apprentissage", "mode statique"],
     "learning", "enabled", False),
    (["réactive l'apprentissage", "apprends de moi", "mode adaptatif"],
     "learning", "enabled", True),

    # --- Énergie ---
    (["tu sembles fatigué", "sois plus énergique", "réveille-toi"],
     None, "energy_level", "high"),
    (["calme-toi", "moins d'énergie", "sois plus calme"],
     None, "energy_level", "low"),
    (["énergie normale", "niveau normal"],
     None, "energy_level", "normal"),

    # --- Humeur ---
    (["tu vas bien", "mode normal", "humeur normale"],
     None, "mood", "neutre"),
    (["sois positif", "bonne humeur", "optimiste"],
     None, "mood", "positif"),
    (["mode focus", "concentration", "sois sérieux"],
     None, "mood", "focus"),
]

# Valeurs autorisées par champ.
# - Champs énumérés (str) : set de valeurs valides
# - Champs booléens : {True, False} — refuse toute valeur non-booléenne
ALLOWED_VALUES: dict[str, set] = {
    # Énumérés
    "verbosity":    {"low", "medium", "high"},
    "tone":         {"technique", "direct", "bienveillant"},
    "energy_level": {"low", "normal", "high"},
    "mood":         {"neutre", "positif", "focus"},
    # Booléens
    "proactive":             {True, False},
    "suggest_improvements":  {True, False},
    "enabled":               {True, False},
}


# ---------------------------------------------------------------------------
# Cache des champs protégés
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _resolve_protected() -> frozenset:
    """
    Résout les champs protégés en lisant le YAML UNE SEULE FOIS
    pour toute la durée de vie du processus (lru_cache).
    Retourne un frozenset (hashable, requis par lru_cache).
    Pour invalider : _resolve_protected.cache_clear()
    """
    try:
        base = _load_yaml_base()
        return frozenset(_get_protected_fields(base))
    except Exception:
        logger.warning("[UPDATER] YAML inaccessible pour _resolve_protected — fallback minimal.")
        return frozenset({"name", "role", "core_identity"})


# ---------------------------------------------------------------------------
# Écriture SQLite
# ---------------------------------------------------------------------------

def _write_field(conn, key: str, value: Any, reason: str,
                 protected: frozenset) -> bool:
    """
    Écrit un champ dans SQLite et journalise le changement.
    Retourne True si l'écriture a eu lieu, False sinon.

    Gardes :
    1. Champ protégé → refus
    2. Valeur hors ALLOWED_VALUES → refus (couvre str ET booléens)
    3. Valeur identique à l'ancienne → no-op silencieux
    """
    # ── Garde 1 : champ protégé ───────────────────────────────────────────
    if key in protected:
        logger.warning(f"[UPDATER] Écriture refusée — champ protégé : '{key}'.")
        return False

    # ── Garde 2 : validation des valeurs autorisées ───────────────────────
    # Pour les champs booléens, Python considère 1==True et 0==False,
    # ce qui laisserait passer des entiers. On exige isinstance(value, bool).
    if key in ALLOWED_VALUES:
        allowed = ALLOWED_VALUES[key]
        is_bool_field = allowed == {True, False}
        if is_bool_field and not isinstance(value, bool):
            logger.warning(
                f"[UPDATER] Type invalide pour '{key}' : {value!r} ({type(value).__name__}). "
                "Booléen strict requis. Écriture refusée."
            )
            return False
        if not is_bool_field and value not in allowed:
            logger.warning(
                f"[UPDATER] Valeur invalide pour '{key}' : {value!r}. "
                f"Valeurs autorisées : {allowed}. Écriture refusée."
            )
            return False

    old_value = _read_field(conn, key)

    # ── Garde 3 : no-op ───────────────────────────────────────────────────
    if old_value == value:
        logger.debug(f"[UPDATER] No-op '{key}' — valeur déjà à {value!r}.")
        return False

    serialized = json.dumps(value)
    conn.execute(
        "INSERT OR REPLACE INTO persona_state(key, value) VALUES (?, ?)",
        (key, serialized)
    )
    conn.execute(
        """INSERT INTO persona_history(timestamp, field, old_value, new_value, reason)
           VALUES (?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).isoformat(),
            key,
            json.dumps(old_value),
            serialized,
            reason,
        )
    )
    conn.commit()
    logger.info(f"[UPDATER] {key}: {old_value!r} → {value!r} (raison: {reason!r})")
    return True


def _write_nested(conn, section: str, field: str, value: Any,
                  reason: str, protected: frozenset) -> bool:
    """
    Met à jour un champ imbriqué (ex: communication.verbosity).
    Valide la valeur sur le champ feuille avant de reconstruire la section.
    """
    # Validation préalable sur le champ feuille (même logique que _write_field)
    if field in ALLOWED_VALUES:
        allowed = ALLOWED_VALUES[field]
        is_bool_field = allowed == {True, False}
        if is_bool_field and not isinstance(value, bool):
            logger.warning(
                f"[UPDATER] Type invalide pour '{section}.{field}' : {value!r} ({type(value).__name__}). "
                "Booléen strict requis. Écriture refusée."
            )
            return False
        if not is_bool_field and value not in allowed:
            logger.warning(
                f"[UPDATER] Valeur invalide pour '{section}.{field}' : {value!r}. "
                f"Valeurs autorisées : {allowed}. Écriture refusée."
            )
            return False

    current = _read_field(conn, section) or {}
    if not isinstance(current, dict):
        current = {}

    # No-op check sur le champ feuille
    if current.get(field) == value:
        logger.debug(f"[UPDATER] No-op '{section}.{field}' — valeur déjà à {value!r}.")
        return False

    current[field] = value
    return _write_field(conn, section, current, reason, protected)


# ---------------------------------------------------------------------------
# Analyse d'intention
# ---------------------------------------------------------------------------

def _analyse_intent(feedback: str) -> list[dict]:
    """Analyse le feedback et retourne la liste des changements candidats."""
    text = feedback.lower().strip()
    changes = []
    for keywords, section, field, value in INTENT_MATRIX:
        for kw in keywords:
            if kw in text:
                changes.append({
                    "section":        section,
                    "field":          field,
                    "value":          value,
                    "matched_phrase": kw,
                })
                break
    return changes


# ---------------------------------------------------------------------------
# Points d'entrée publics
# ---------------------------------------------------------------------------

def update_from_feedback(feedback: str) -> dict:
    """
    Analyse l'intention du feedback et met à jour l'état.
    conn.close() garanti via finally.

    Correction v7 :
    - Retourne status='no_change' si aucune écriture effective n'a eu lieu
      (tous no-ops ou refus), au lieu de 'updated' avec changes=[].
    """
    changes = _analyse_intent(feedback)

    if not changes:
        logger.info(f"[UPDATER] Aucune intention reconnue dans : {feedback!r}")
        return {"status": "no_change", "feedback": feedback, "changes": []}

    protected = _resolve_protected()
    conn = None

    try:
        conn = _init_db()
        applied = []

        for change in changes:
            section = change["section"]
            field   = change["field"]
            value   = change["value"]
            reason  = f"feedback utilisateur — déclencheur: '{change['matched_phrase']}'"

            written = (
                _write_field(conn, field, value, reason, protected)
                if section is None
                else _write_nested(conn, section, field, value, reason, protected)
            )

            if written:
                applied.append({
                    "field":     f"{section}.{field}" if section else field,
                    "new_value": value,
                    "trigger":   change["matched_phrase"],
                })

        # ── Status sémantiquement correct ────────────────────────────────
        status = "updated" if applied else "no_change"
        return {"status": status, "feedback": feedback, "changes": applied}

    except Exception as e:
        logger.error(f"[UPDATER] Erreur lors de la mise à jour : {e}")
        return {"status": "error", "error": str(e), "feedback": feedback, "changes": []}

    finally:
        if conn is not None:
            conn.close()


def force_update(section: str | None, field: str, value: Any,
                 reason: str = "mise à jour forcée") -> dict:
    """Mise à jour directe sans analyse d'intention."""
    protected = _resolve_protected()

    if field in protected or (section and section in protected):
        return {"status": "refused", "reason": "champ protégé par core_identity"}

    conn = None
    try:
        conn = _init_db()
        written = (
            _write_field(conn, field, value, reason, protected)
            if section is None
            else _write_nested(conn, section, field, value, reason, protected)
        )
        return {
            "status": "updated" if written else "no_change",
            "field":  f"{section}.{field}" if section else field,
            "value":  value,
        }
    except Exception as e:
        logger.error(f"[UPDATER] force_update échoué : {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if conn is not None:
            conn.close()
