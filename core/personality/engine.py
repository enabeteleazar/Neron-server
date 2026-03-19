"""
engine.py — Construction du prompt système pour Neron
Intègre la persona complète (base YAML + état dynamique SQLite).

Corrections v5 :
- Valeurs mood/energy_level inconnues gèrent un fallback cohérent :
  label affiché + instruction générique explicite au lieu d'une instruction
  silencieusement incohérente avec la valeur.
"""

import logging

from .loader import load_persona
from .constants import ENERGY_INSTRUCTIONS, MOOD_INSTRUCTIONS

logger = logging.getLogger(__name__)

# Instruction générique pour toute valeur non référencée dans les dicts constants
_UNKNOWN_MOOD_HINT   = "Adapte ton comportement selon le contexte de la conversation."
_UNKNOWN_ENERGY_HINT = "Maintiens un équilibre entre clarté et concision."


def build_system_prompt(user_context: str = "") -> str:
    """
    Construit le prompt système complet à partir de la persona active.
    - Traits et règles formatés en liste à tirets
    - État dynamique (mood, energy_level, learning) avec instructions concrètes
    - Valeurs inconnues pour mood/energy_level → instruction générique cohérente
    """
    try:
        persona = load_persona()
    except RuntimeError as e:
        return (
            f"[ERREUR MODULE PERSONALITY]\n{e}\n\n"
            "Le module de personnalité n'a pas pu être chargé. "
            "Répondez de façon neutre et informez l'utilisateur du problème."
        )

    # --- Traits (liste à tirets) ---
    traits_raw = persona.get("traits", [])
    traits_block = "\n".join(f"- {t}" for t in traits_raw) \
        if isinstance(traits_raw, list) else f"- {traits_raw}"

    # --- Règles (liste à tirets) ---
    rules_raw = persona.get("rules", [])
    rules_block = "\n".join(f"- {r}" for r in rules_raw) \
        if isinstance(rules_raw, list) else f"- {rules_raw}"

    # --- Paramètres dynamiques ---
    comm         = persona.get("communication", {})
    behavior     = persona.get("behavior", {})
    learning     = persona.get("learning", {})
    mood         = persona.get("mood", "neutre")
    energy_level = persona.get("energy_level", "normal")

    # --- Instructions mood / energy avec fallback explicite ─────────────────
    # Si la valeur est connue → instruction spécifique
    # Si inconnue (ex: 'irrité', valeur custom) → instruction générique
    #   + log warning pour alerter le développeur
    if mood not in MOOD_INSTRUCTIONS:
        logger.warning(
            f"[ENGINE] Valeur mood inconnue : '{mood}'. "
            f"Valeurs reconnues : {list(MOOD_INSTRUCTIONS.keys())}. "
            "Instruction générique appliquée."
        )
    mood_hint = MOOD_INSTRUCTIONS.get(mood, _UNKNOWN_MOOD_HINT)

    if energy_level not in ENERGY_INSTRUCTIONS:
        logger.warning(
            f"[ENGINE] Valeur energy_level inconnue : '{energy_level}'. "
            f"Valeurs reconnues : {list(ENERGY_INSTRUCTIONS.keys())}. "
            "Instruction générique appliquée."
        )
    energy_hint = ENERGY_INSTRUCTIONS.get(energy_level, _UNKNOWN_ENERGY_HINT)

    # --- Bloc apprentissage ---
    learning_enabled = learning.get("enabled", True)
    learning_hint = (
        "Tu peux adapter ton comportement en fonction des retours de l'utilisateur."
        if learning_enabled
        else "Mode statique actif — ne modifie pas ton comportement selon les retours."
    )

    prompt = f"""\
Tu es {persona.get('name', 'Neron')}, {persona.get('role', 'assistant')}.

## Traits de personnalité
{traits_block}

## Style de communication
- Ton : {comm.get('tone', 'technique')}
- Niveau de détail : {comm.get('verbosity', 'medium')}
- Format : {comm.get('format', 'structuré')}

## État dynamique
- Humeur : {mood} — {mood_hint}
- Énergie : {energy_level} — {energy_hint}

## Comportement
- Proactif : {behavior.get('proactive', True)}
- Propose des améliorations : {behavior.get('suggest_improvements', True)}

## Apprentissage
- {learning_hint}

## Règles
{rules_block}

## Contexte utilisateur
{user_context if user_context else "Aucun contexte supplémentaire fourni."}
"""

    return prompt.strip()
