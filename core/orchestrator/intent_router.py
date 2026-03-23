# orchestrator/intent_router.py

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum

from agents.base_agent import get_logger

logger = get_logger(__name__)


class Intent(str, Enum):
    CONVERSATION         = "conversation"
    WEB_SEARCH           = "web_search"
    HA_ACTION            = "ha_action"
    TIME_QUERY           = "time_query"
    PERSONALITY_FEEDBACK = "personality_feedback"
    CODE                 = "code"  # FIX: tabulation mixte supprimée


@dataclass
class IntentResult:
    intent:     Intent
    confidence: str


# ── Mots-clés feedback comportemental ────────────────────────────────────────
# Synchronisés avec l'INTENT_MATRIX de core/personality/updater.py

_PERSONALITY_KEYWORDS = [
    "trop long", "trop verbeux", "trop bavard", "raccourcis", "sois bref",
    "plus de détail", "développe", "explique mieux", "trop court",
    "niveau ok", "longueur ok",
    "sois direct", "va droit au but", "sans détour", "sans blabla",
    "plus doux", "sois plus sympa", "moins froid", "plus chaleureux",
    "redeviens technique", "mode technique", "sois technique",
    "arrête de proposer", "moins de suggestions", "pas de suggestions",
    "sois proactif", "propose plus", "anticipe",
    "arrête d'apprendre", "désactive l'apprentissage", "mode statique",
    "réactive l'apprentissage", "apprends de moi", "mode adaptatif",
    "tu sembles fatigué", "sois plus énergique", "réveille-toi",
    "calme-toi", "moins d'énergie", "sois plus calme",
    "énergie normale", "niveau normal",
    "mode normal", "humeur normale",
    "sois positif", "bonne humeur", "optimiste",
    "mode focus", "concentration", "sois sérieux",
]

# FIX: mots-clés code revus — suppression des termes trop courts ou ambigus
# ("code", "module", "classe", "fonction" généraient des faux positifs sur
# des messages comme "Ça va, je m'occupe de corriger ton code source")
# Tous les déclencheurs sont désormais des expressions d'au moins 5 caractères
# décrivant une action explicite de développement.
_CODE_KEYWORDS = [
    # Actions explicites de génération
    "génère", "genere",
    "crée un fichier", "cree un fichier",
    "écris un script", "ecris un script",
    "écris un module", "ecris un module",
    "écris une classe", "ecris une classe",
    "écris une fonction", "ecris une fonction",
    # Actions explicites d'amélioration / analyse
    "améliore le fichier", "ameliore le fichier",
    "améliore ce code", "ameliore ce code",
    "optimise le fichier", "optimise ce code",
    "corrige le fichier", "corrige ce code",
    "refactorise",
    "analyse le fichier", "analyse ce code",
    "inspecte le fichier",
    "qualité du code", "qualite du code",
    # Lecture de fichier
    "lis le fichier", "montre le code", "affiche le fichier",
    # Revue / rollback
    "self review", "auto review", "revue de code",
    "passe en revue", "rollback", "restaure le fichier",
]

# Longueur minimale d'un déclencheur code pour éviter les faux positifs
_CODE_KW_MIN_LEN = 5


def _normalize(text: str) -> str:
    """Normalise : minuscules + suppression des accents."""
    n = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in n if unicodedata.category(c) != "Mn")


class IntentRouter:
    def __init__(self, llm_agent=None) -> None:
        self.llm_agent = llm_agent

    async def route(self, query: str) -> IntentResult:
        q_norm = _normalize(query)

        # ── Feedback comportemental (priorité haute) ──────────────────────
        for kw in _PERSONALITY_KEYWORDS:
            if _normalize(kw) in q_norm:
                logger.info("[ROUTER] intent=personality_feedback — déclencheur: %r", kw)
                return IntentResult(
                    intent=Intent.PERSONALITY_FEEDBACK,
                    confidence="high",
                )

        # ── Code / développement ──────────────────────────────────────────
        # FIX: vérification longueur minimale + expressions explicites uniquement
        for kw in _CODE_KEYWORDS:
            kw_norm = _normalize(kw)
            if len(kw_norm) >= _CODE_KW_MIN_LEN and kw_norm in q_norm:
                logger.info("[ROUTER] intent=code — déclencheur: %r", kw)
                return IntentResult(intent=Intent.CODE, confidence="high")

        # ── Heure / date ──────────────────────────────────────────────────
        if any(w in q_norm for w in [
            "quelle heure", "il est quelle heure",
            "quelle heure est il", "donne moi l heure",
            "quel jour sommes", "on est quel jour",
            "quel mois sommes", "quelle date sommes",
            "donne moi la date", "c est quoi la date",
            "on est le combien",
        ]):
            return IntentResult(intent=Intent.TIME_QUERY, confidence="high")

        # ── Recherche web ─────────────────────────────────────────────────
        if any(w in q_norm for w in [
            "cherche", "recherche", "google", "web",
            "actualite", "news", "meteo",
        ]):
            return IntentResult(intent=Intent.WEB_SEARCH, confidence="high")

        # ── Home Assistant ────────────────────────────────────────────────
        if any(w in q_norm for w in [
            "allume", "eteins", "thermostat", "lumiere", "volet", "home assistant",
        ]):
            return IntentResult(intent=Intent.HA_ACTION, confidence="high")

        # ── Conversation générale (défaut) ────────────────────────────────
        return IntentResult(intent=Intent.CONVERSATION, confidence="medium")
