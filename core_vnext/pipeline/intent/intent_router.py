# orchestrator/intent_router.py

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum

from core.agents.base_agent import get_logger
from core.constants import (
    CODE_KEYWORDS,
    CODE_AUDIT_KEYWORDS,
    HA_KEYWORDS,
    PERSONALITY_KEYWORDS,
    TIME_KEYWORDS,
    WEB_KEYWORDS,
)

logger = get_logger(__name__)


class Intent(str, Enum):
    CONVERSATION         = "conversation"
    WEB_SEARCH           = "web_search"
    HA_ACTION            = "ha_action"
    TIME_QUERY           = "time_query"
    PERSONALITY_FEEDBACK = "personality_feedback"
    CODE                 = "code"
    CODE_AUDIT           = "code_audit"


@dataclass
class IntentResult:
    intent:     Intent
    confidence: str


# Toutes les listes de mots-clés sont dans constants.py


def _normalize(text: str) -> str:
    """Normalise : minuscules + suppression des accents + apostrophes → espace."""
    n = unicodedata.normalize("NFD", text.lower().strip())
    # Supprime les marques diacritiques
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    # Apostrophes typographiques et droites → espace
    n = n.replace("'", " ").replace("'", " ").replace("`", " ")
    return n


class IntentRouter:
    def __init__(self, llm_agent=None) -> None:
        self.llm_agent = llm_agent

    async def route(self, query: str) -> IntentResult:
        q_norm = _normalize(query)

        # ── Feedback comportemental (priorité haute) ──────────────────────
        for kw in PERSONALITY_KEYWORDS:
            if _normalize(kw) in q_norm:
                logger.info("[ROUTER] intent=personality_feedback — déclencheur: %r", kw)
                return IntentResult(
                    intent=Intent.PERSONALITY_FEEDBACK,
                    confidence="high",
                )

        # ── Auto-audit Néron (priorité avant CODE générique) ─────────────
        for kw in CODE_AUDIT_KEYWORDS:
            if _normalize(kw) in q_norm:
                logger.info("[ROUTER] intent=code_audit — déclencheur: %r", kw)
                return IntentResult(intent=Intent.CODE_AUDIT, confidence="high")

        # ── Code / développement ──────────────────────────────────────────
        for kw in CODE_KEYWORDS:
            kw_norm = _normalize(kw)
            if kw_norm in q_norm:
                logger.info("[ROUTER] intent=code — déclencheur: %r", kw)
                return IntentResult(intent=Intent.CODE, confidence="high")

        # ── Heure / date ──────────────────────────────────────────────────
        if any(_normalize(w) in q_norm for w in TIME_KEYWORDS):
            return IntentResult(intent=Intent.TIME_QUERY, confidence="high")

        # ── Recherche web ─────────────────────────────────────────────────
        if any(_normalize(w) in q_norm for w in WEB_KEYWORDS):
            return IntentResult(intent=Intent.WEB_SEARCH, confidence="high")

        # ── Home Assistant ────────────────────────────────────────────────
        if any(_normalize(w) in q_norm for w in HA_KEYWORDS):
            return IntentResult(intent=Intent.HA_ACTION, confidence="high")

        # ── Conversation générale (défaut) ────────────────────────────────
        return IntentResult(intent=Intent.CONVERSATION, confidence="medium")

