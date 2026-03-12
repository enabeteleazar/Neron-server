# tests/test_orchestrator.py
import pytest
from orchestrator.intent_router import IntentRouter, Intent, IntentResult


@pytest.fixture
def router():
    return IntentRouter(llm_agent=None)


@pytest.mark.asyncio
async def test_intent_conversation(router):
    result = await router.route("bonjour comment tu vas")
    assert result.intent == Intent.CONVERSATION


@pytest.mark.asyncio
async def test_intent_web_search_cherche(router):
    result = await router.route("cherche des infos sur Python")
    assert result.intent == Intent.WEB_SEARCH


@pytest.mark.asyncio
async def test_intent_web_search_meteo(router):
    result = await router.route("quelle est la meteo aujourd hui")
    assert result.intent == Intent.WEB_SEARCH


@pytest.mark.asyncio
async def test_intent_ha_action_lumiere(router):
    result = await router.route("allume la lumiere du salon")
    assert result.intent == Intent.HA_ACTION


@pytest.mark.asyncio
async def test_intent_ha_action_thermostat(router):
    result = await router.route("eteins le thermostat")
    assert result.intent == Intent.HA_ACTION


@pytest.mark.asyncio
async def test_intent_result_values(router):
    result = await router.route("bonjour")
    assert isinstance(result, IntentResult)
    assert result.confidence in ["low", "medium", "high"]


@pytest.mark.asyncio
async def test_intent_enum_members(router):
    assert Intent.CONVERSATION == "conversation"
    assert Intent.WEB_SEARCH == "web_search"
    assert Intent.HA_ACTION == "ha_action"
    assert Intent.TIME_QUERY == "time_query"
