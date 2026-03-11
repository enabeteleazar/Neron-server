# orchestrator/intent_router.py
from enum import Enum
from dataclasses import dataclass
from agents.base_agent import get_logger

logger = get_logger(__name__)


class Intent(str, Enum):
    CONVERSATION = "conversation"
    WEB_SEARCH = "web_search"
    HA_ACTION = "ha_action"
    TIME_QUERY = "time_query"


@dataclass
class IntentResult:
    intent: Intent
    confidence: str


class IntentRouter:
    def __init__(self, llm_agent=None):
        self.llm_agent = llm_agent

    async def route(self, query: str) -> IntentResult:
        import unicodedata
        q = unicodedata.normalize("NFD", query.lower().strip())
        q = "".join(c for c in q if unicodedata.category(c) != "Mn")

        if any(w in q for w in [
            "heure", "quelle heure", "il est quelle heure",
            "date", "quel jour", "on est le", "quel mois"
        ]):
            return IntentResult(intent=Intent.TIME_QUERY, confidence="high")

        if any(w in q for w in [
            "cherche", "recherche", "google", "web",
            "actualite", "news", "meteo"
        ]):
            return IntentResult(intent=Intent.WEB_SEARCH, confidence="high")

        if any(w in q for w in [
            "allume", "eteins", "thermostat", "lumiere", "volet", "home assistant"
        ]):
            return IntentResult(intent=Intent.HA_ACTION, confidence="high")

        return IntentResult(intent=Intent.CONVERSATION, confidence="medium")
