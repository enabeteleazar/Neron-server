"""
loader.py — Chargement de la persona Neron
Fusionne persona.yaml (config de base) avec l'état SQLite (état dynamique).
Protège les champs définis dans core_identity.protected_fields du YAML.

Corrections v5 :
- _safe_json_load centralisé ici (unique point de désérialisation JSON)
- Exporté pour __init__.py (get_history)
"""

import yaml
import json
import sqlite3
import logging
from pathlib import Path

from .constants import DB_FILENAME, DEFAULTS

logger = logging.getLogger(__name__)

BASE_PATH        = Path(__file__).parent
DB_PATH          = BASE_PATH / DB_FILENAME
YAML_PATH        = BASE_PATH / "persona.yaml"
JSON_FALLBACK_PATH = BASE_PATH / "persona_state.json"


# ---------------------------------------------------------------------------
# Utilitaire JSON partagé
# ---------------------------------------------------------------------------

def _safe_json_load(value: str | None):
    """
    Parse JSON silencieusement.
    Retourne la valeur brute en cas d'échec, None si valeur absente.
    Centralisé ici pour éviter toute duplication dans __init__.py.
    """
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------

def _init_db() -> sqlite3.Connection:
    """Initialise la base SQLite et crée les tables si elles n'existent pas."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS persona_state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS persona_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            field     TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            reason    TEXT
        )
    """)
    conn.commit()

    # Seed initial depuis JSON si la table est vide
    cursor = conn.execute("SELECT COUNT(*) FROM persona_state")
    if cursor.fetchone()[0] == 0:
        try:
            with open(JSON_FALLBACK_PATH, encoding="utf-8") as f:
                seed = json.load(f)
            for key, value in seed.items():
                if key != "history":
                    conn.execute(
                        "INSERT OR IGNORE INTO persona_state(key, value) VALUES (?, ?)",
                        (key, json.dumps(value))
                    )
            conn.commit()
            logger.info("persona_state.db initialisée depuis persona_state.json")
        except Exception as e:
            logger.warning(f"Impossible de seeder la DB depuis JSON : {e}")

    return conn


def _read_field(conn: sqlite3.Connection, key: str):
    """Lit un champ depuis SQLite. Retourne None si absent."""
    cursor = conn.execute("SELECT value FROM persona_state WHERE key = ?", (key,))
    row = cursor.fetchone()
    if row is None:
        return None
    return _safe_json_load(row[0])


def _load_db_state(conn: sqlite3.Connection) -> dict:
    """Charge l'état dynamique complet depuis SQLite."""
    state = {}
    try:
        cursor = conn.execute("SELECT key, value FROM persona_state")
        for key, value in cursor.fetchall():
            state[key] = _safe_json_load(value)
    except Exception as e:
        logger.warning(f"[PERSONA] Lecture SQLite échouée : {e}")
    return state


# ---------------------------------------------------------------------------
# YAML
# ---------------------------------------------------------------------------

def _load_yaml_base() -> dict:
    """Charge persona.yaml avec messages d'erreur explicites."""
    try:
        with open(YAML_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError("persona.yaml ne contient pas un mapping valide.")
        return data
    except FileNotFoundError:
        logger.error(f"[PERSONA] Fichier introuvable : {YAML_PATH}")
        raise RuntimeError(
            f"[PERSONA ERREUR] persona.yaml est manquant ({YAML_PATH}). "
            "Vérifiez l'installation du module personality."
        )
    except yaml.YAMLError as e:
        logger.error(f"[PERSONA] Erreur de parsing YAML : {e}")
        raise RuntimeError(
            f"[PERSONA ERREUR] persona.yaml est corrompu ou mal formaté.\n"
            f"Détail : {e}"
        )
    except Exception as e:
        logger.error(f"[PERSONA] Erreur inattendue lors du chargement YAML : {e}")
        raise RuntimeError(f"[PERSONA ERREUR] Chargement impossible : {e}")


def _get_protected_fields(yaml_base: dict) -> set:
    """
    Lit les champs protégés depuis core_identity.protected_fields dans le YAML.
    C'est cette liste qui fait autorité — constants.py ne la duplique plus.
    Fallback sur un set minimal si le champ est absent ou mal formé.
    """
    try:
        fields = yaml_base.get("core_identity", {}).get("protected_fields", [])
        if isinstance(fields, list) and fields:
            return set(fields)
    except Exception:
        pass
    logger.warning(
        "[PERSONA] core_identity.protected_fields absent ou invalide — fallback minimal."
    )
    return {"name", "role", "core_identity"}


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

def load_persona() -> dict:
    """
    Charge et fusionne la persona complète.
    - Lit persona.yaml UNE SEULE FOIS
    - Champs protégés lus dynamiquement depuis core_identity.protected_fields
    - DEFAULTS appliqués pour tout champ manquant
    - Protection réimposée en fin de fusion
    """
    # ── 1. Chargement YAML — une seule fois ──────────────────────────────────
    base = _load_yaml_base()

    # ── 2. Champs protégés sauvegardés avant toute fusion ────────────────────
    protected = _get_protected_fields(base)
    protected_values = {f: base[f] for f in protected if f in base}

    # ── 3. Chargement de l'état SQLite ───────────────────────────────────────
    conn = None
    try:
        conn = _init_db()
        state = _load_db_state(conn)
    except Exception as e:
        logger.warning(f"[PERSONA] SQLite inaccessible, utilisation YAML seule : {e}")
        state = {}
    finally:
        if conn is not None:
            conn.close()

    # ── 4. Fusion des sections dynamiques + DEFAULTS ─────────────────────────
    for section in ("communication", "behavior", "learning"):
        db_section = state.get(section)
        if isinstance(db_section, dict):
            base.setdefault(section, {}).update(db_section)
        for k, v in DEFAULTS.get(section, {}).items():
            base.setdefault(section, {}).setdefault(k, v)

    # ── 5. Champs de premier niveau (mood, energy_level) ─────────────────────
    for field in ("mood", "energy_level"):
        base[field] = state.get(field, DEFAULTS.get(field))

    # ── 6. Réimpose les champs protégés (jamais écrasables par SQLite) ───────
    base.update(protected_values)

    return base
