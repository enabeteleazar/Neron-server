# core/pipeline/intent/intent_router.py

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict

from core.agents.base_agent import get_logger

logger = get_logger(__name__)


def _nlp():
    from core.pipeline.nlp.nlp_processor import get_processor
    return get_processor()


class Intent(str, Enum):
    CONVERSATION         = "conversation"
    WEB_SEARCH           = "web_search"
    HA_ACTION            = "ha_action"
    TIME_QUERY           = "time_query"
    PERSONALITY_FEEDBACK = "personality_feedback"
    CODE                 = "code"
    CODE_AUDIT           = "code_audit"

    AGENT_CREATION       = "agent_creation"
    AGENT_LIST           = "agent_list"
    AGENT_RUN            = "agent_run"

    SYSTEM_STATUS        = "system_status"
    NETWORK_STATUS       = "network_status"

    NEWS_QUERY           = "news_query"
    WEATHER_QUERY        = "weather_query"
    TODO_ACTION          = "todo_action"
    WIKI_QUERY           = "wiki_query"


_INTENT_MAP: Dict[str, Intent] = {i.value: i for i in Intent}


@dataclass
class IntentResult:
    intent: Intent
    confidence: str
    confidence_score: float = 0.0
    entities: Dict[str, Any] = field(default_factory=dict)

    def to_nlp_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "entities": self.entities,
            "confidence": self.confidence_score,
        }


def _normalize(text: str) -> str:
    n = unicodedata.normalize("NFD", text.lower().strip())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    return n.replace("'", " ").replace("’", " ").replace("`", " ")


def _fallback_intent(query: str) -> Intent | None:
    q = _normalize(query)

    system_keywords = [
        "statut systeme",
        "etat systeme",
        "status systeme",
        "services actifs",
        "liste les services",
    ]

    network_keywords = [
        "ports ouverts",
        "etat reseau",
        "status reseau",
    ]

    agent_creation_keywords = [
        "cree un agent",
        "crée un agent",
        "nouvel agent",
        "genere un agent",
        "génère un agent",
    ]

    agent_list_keywords = [
        "liste les agents",
        "agents disponibles",
        "quels agents",
        "montre les agents",
    ]

    agent_run_keywords = [
        "lance l agent",
        "lance l'agent",
        "lance agent",
        "execute l agent",
        "execute l'agent",
        "execute agent",
        "exécute l agent",
        "exécute l'agent",
        "run agent",
    ]

    if any(k in q for k in system_keywords):
        return Intent.SYSTEM_STATUS

    if any(k in q for k in network_keywords):
        return Intent.NETWORK_STATUS

    if any(k in q for k in agent_creation_keywords):
        return Intent.AGENT_CREATION

    if any(k in q for k in agent_list_keywords):
        return Intent.AGENT_LIST

    if any(k in q for k in agent_run_keywords):
        return Intent.AGENT_RUN

    return None


class IntentRouter:
    def __init__(self, llm_agent=None) -> None:
        self.llm_agent = llm_agent

    async def route(self, query: str) -> IntentResult:
        nlp_result = _nlp().process(query)

        intent_str = nlp_result.intent
        intent = _INTENT_MAP.get(intent_str, Intent.CONVERSATION)

        entities = nlp_result.entities
        score = nlp_result.confidence

        fallback = _fallback_intent(query)

        if fallback and (intent == Intent.CONVERSATION or score < 0.70):
            intent = fallback
            intent_str = fallback.value
            score = max(score, 0.85)

        confidence = (
            "high"
            if score >= 0.7
            else ("medium" if score >= 0.4 else "low")
        )

        logger.info(
            "[NLP] intent=%s confidence=%.3f entities=%s",
            intent_str,
            score,
            entities,
        )

        return IntentResult(
            intent=intent,
            confidence=confidence,
            confidence_score=score,
            entities=entities,
        )
