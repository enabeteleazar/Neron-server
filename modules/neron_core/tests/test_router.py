# tests/test_router.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from orchestrator.intent_router import IntentRouter, Intent


@pytest.fixture
def router():
    return IntentRouter(llm_agent=None)


# --- WEB_SEARCH ---

@pytest.mark.asyncio
async def test_web_search_cherche(router):
    result = await router.route("cherche des infos sur Python")
    assert result.intent == Intent.WEB_SEARCH
    assert result.confidence == "high"


@pytest.mark.asyncio
async def test_web_search_meteo(router):
    result = await router.route("quelle est la meteo demain")
    assert result.intent == Intent.WEB_SEARCH
    assert result.confidence == "high"


@pytest.mark.asyncio
async def test_web_search_news(router):
    result = await router.route("les news du jour")
    assert result.intent == Intent.WEB_SEARCH
    assert result.confidence == "high"


# --- HA_ACTION ---

@pytest.mark.asyncio
async def test_ha_action_allume(router):
    result = await router.route("allume la lumiere")
    assert result.intent == Intent.HA_ACTION
    assert result.confidence == "high"


@pytest.mark.asyncio
async def test_ha_action_eteins(router):
    result = await router.route("eteins le thermostat")
    assert result.intent == Intent.HA_ACTION
    assert result.confidence == "high"


# --- CONVERSATION ---

@pytest.mark.asyncio
async def test_conversation_fallback(router):
    result = await router.route("bonjour comment tu vas")
    assert result.intent == Intent.CONVERSATION


@pytest.mark.asyncio
async def test_conversation_aide(router):
    result = await router.route("aide moi a ecrire un email")
    assert result.intent == Intent.CONVERSATION


# --- Types de retour ---

@pytest.mark.asyncio
async def test_result_has_intent(router):
    result = await router.route("bonjour")
    assert hasattr(result, "intent")


@pytest.mark.asyncio
async def test_result_has_confidence(router):
    result = await router.route("bonjour")
    assert hasattr(result, "confidence")
