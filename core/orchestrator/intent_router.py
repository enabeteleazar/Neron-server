# orchestrator/intent_router.py
#
# Intégration module personality v7 :
# - Nouvel intent PERSONALITY_FEEDBACK pour intercepter les feedbacks comportementaux
#   ("sois bref", "mode focus", "tu sembles fatigué"…) avant qu'ils n'atteignent le LLM
# - Les mots-clés sont synchronisés avec l'INTENT_MATRIX du module personality

import unicodedata
from enum import Enum
from dataclasses import dataclass
from agents.base_agent import get_logger

logger = get_logger(__name__)


class Intent(str, Enum):
    CONVERSATION        = "conversation"
    WEB_SEARCH          = "web_search"
    HA_ACTION           = "ha_action"
    TIME_QUERY          = "time_query"
    PERSONALITY_FEEDBACK = "personality_feedback"   # ← nouveau


@dataclass
class IntentResult:
    intent:     Intent
    confidence: str


# ---------------------------------------------------------------------------
# Mots-clés de feedback comportemental
# Synchronisés avec l'INTENT_MATRIX de core/personality/updater.py
# ---------------------------------------------------------------------------
_PERSONALITY_KEYWORDS = [
    # Verbosité
    "trop long", "trop verbeux", "trop bavard", "raccourcis", "sois bref",
    "plus de détail", "développe", "explique mieux", "trop court",
    "niveau ok", "longueur ok",
    # Ton
    "sois direct", "va droit au but", "sans détour", "sans blabla",
    "plus doux", "sois plus sympa", "moins froid", "plus chaleureux",
    "redeviens technique", "mode technique", "sois technique",
    # Proactivité
    "arrête de proposer", "moins de suggestions", "pas de suggestions",
    "sois proactif", "propose plus", "anticipe",
    # Apprentissage
    "arrête d'apprendre", "désactive l'apprentissage", "mode statique",
    "réactive l'apprentissage", "apprends de moi", "mode adaptatif",
    # Énergie
    "tu sembles fatigué", "sois plus énergique", "réveille-toi",
    "calme-toi", "moins d'énergie", "sois plus calme",
    "énergie normale", "niveau normal",
    # Humeur
    "mode normal", "humeur normale",
    "sois positif", "bonne humeur", "optimiste",
    "mode focus", "concentration", "sois sérieux",
]


def _normalize(text: str) -> str:
    """Normalise : minuscules + suppression des accents."""
    n = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in n if unicodedata.category(c) != "Mn")


class IntentRouter:
    def __init__(self, llm_agent=None):
        self.llm_agent = llm_agent

    async def route(self, query: str) -> IntentResult:
        q_raw  = query.lower().strip()
        q_norm = _normalize(query)

        # ── 1. Feedback comportemental (priorité haute) ───────────────────
        # Vérifié en premier : un "sois bref" ne doit pas partir au LLM
        for kw in _PERSONALITY_KEYWORDS:
            kw_norm = _normalize(kw)
            if kw_norm in q_norm:
                logger.info(f"[ROUTER] intent=personality_feedback — déclencheur: {kw!r}")
                return IntentResult(
                    intent=Intent.PERSONALITY_FEEDBACK,
                    confidence="high"
                )

        # ── 2. Heure / date ───────────────────────────────────────────────
        if any(w in q_norm for w in [
            "heure", "quelle heure", "il est quelle heure",
            "date", "quel jour", "on est le", "quel mois"
        ]):
            return IntentResult(intent=Intent.TIME_QUERY, confidence="high")

        # ── 3. Recherche web ──────────────────────────────────────────────
        if any(w in q_norm for w in [
            "cherche", "recherche", "google", "web",
            "actualite", "news", "meteo"
        ]):
            return IntentResult(intent=Intent.WEB_SEARCH, confidence="high")

        # ── 4. Home Assistant ─────────────────────────────────────────────
        if any(w in q_norm for w in [
            "allume", "eteins", "thermostat", "lumiere", "volet", "home assistant"
        ]):
            return IntentResult(intent=Intent.HA_ACTION, confidence="high")

        # ── 5. Conversation générale ──────────────────────────────────────
        return IntentResult(intent=Intent.CONVERSATION, confidence="medium")
