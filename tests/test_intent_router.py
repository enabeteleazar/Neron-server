# tests/test_intent_router.py
# Tests pour core/orchestrator/intent_router.py

import pytest
from serverVNext.serverVNext.core.orchestrator.intent_router import IntentRouter, Intent, IntentResult


class TestIntentRouter:
    @pytest.fixture
    def router(self):
        return IntentRouter()

    def test_router_initialization(self, router):
        assert router.llm_agent is None

    @pytest.mark.asyncio
    async def test_route_conversation(self, router):
        result = await router.route("Bonjour, comment ça va?")
        assert isinstance(result, IntentResult)
        assert result.intent == Intent.CONVERSATION
        assert result.confidence in ["high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_route_web_search(self, router):
        result = await router.route("Recherche sur internet comment faire du café")
        assert result.intent == Intent.WEB_SEARCH

    @pytest.mark.asyncio
    async def test_route_code(self, router):
        result = await router.route("Écris une fonction Python pour calculer fibonacci")
        assert result.intent == Intent.CODE

    @pytest.mark.asyncio
    async def test_route_ha_action(self, router):
        result = await router.route("Allume la lumière du salon")
        assert result.intent == Intent.HA_ACTION

    @pytest.mark.asyncio
    async def test_route_time_query(self, router):
        result = await router.route("Quelle heure est-il?")
        assert result.intent == Intent.TIME_QUERY

    @pytest.mark.asyncio
    async def test_route_personality(self, router):
        result = await router.route("Je n'aime pas tes réponses")
        assert result.intent == Intent.PERSONALITY_FEEDBACK


class TestIntentEnum:
    def test_intent_values(self):
        assert Intent.CONVERSATION == "conversation"
        assert Intent.WEB_SEARCH == "web_search"
        assert Intent.CODE == "code"
        assert Intent.HA_ACTION == "ha_action"
        assert Intent.TIME_QUERY == "time_query"
        assert Intent.PERSONALITY_FEEDBACK == "personality_feedback"

    def test_all_intents_covered(self):
        expected = {
            "conversation", "web_search", "code", "ha_action",
            "time_query", "personality_feedback"
        }
        actual = {intent.value for intent in Intent}
        assert actual == expected