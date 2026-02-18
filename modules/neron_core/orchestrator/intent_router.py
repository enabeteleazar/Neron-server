from enum import Enum
from dataclasses import dataclass
from agents.base_agent import get_logger

logger = get_logger(__name__)


class Intent(str, Enum):
    CONVERSATION = "conversation"
    WEB_SEARCH = "web_search"
    HA_ACTION = "ha_action"


@dataclass
class IntentResult:
    intent: Intent
    confidence: str


class IntentRouter:
    def __init__(self, llm_agent=None):
        self.llm_agent = llm_agent

    async def route(self, query: str) -> IntentResult:
        q = query.lower()
        if any(w in q for w in ["cherche", "recherche", "google", "web", "actualité", "news", "météo"]):
            return IntentResult(intent=Intent.WEB_SEARCH, confidence="high")
        if any(w in q for w in ["allume", "éteins", "thermostat", "lumière", "volet", "home assistant"]):
            return IntentResult(intent=Intent.HA_ACTION, confidence="high")
        return IntentResult(intent=Intent.CONVERSATION, confidence="medium")

