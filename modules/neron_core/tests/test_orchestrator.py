# modules/neron_core/tests/test_orchestrator.py
import pytest
from orchestrator.intent_router import IntentRouter, Intent, IntentResult


@pytest.fixture
def router():
    return IntentRouter(llm_agent=None)


# --- Tests de routing ---

@pytest.mark.asyncio
async def test_intent_conversation(router):
    result = await router.route("Bonjour, comment vas-tu ?")
    assert result.intent == Intent.CONVERSATION
    assert result.confidence == "medium"


@pytest.mark.asyncio
async def test_intent_web_search_cherche(router):
    result = await router.route("Cherche les dernières news sur Python")
    assert result.intent == Intent.WEB_SEARCH
    assert result.confidence == "high"


@pytest.mark.asyncio
async def test_intent_web_search_meteo(router):
    result = await router.route("Quelle est la météo aujourd'hui ?")
    assert result.intent == Intent.WEB_SEARCH
    assert result.confidence == "high"


@pytest.mark.asyncio
async def test_intent_ha_action_lumiere(router):
    result = await router.route("Allume la lumière du salon")
    assert result.intent == Intent.HA_ACTION
    assert result.confidence == "high"


@pytest.mark.asyncio
async def test_intent_ha_action_thermostat(router):
    result = await router.route("Règle le thermostat à 20 degrés")
    assert result.intent == Intent.HA_ACTION
    assert result.confidence == "high"


# --- Tests du modèle IntentResult ---

def test_intent_result_values():
    result = IntentResult(intent=Intent.CONVERSATION, confidence="medium")
    assert result.intent.value == "conversation"


def test_intent_enum_members():
    assert Intent.CONVERSATION == "conversation"
    assert Intent.WEB_SEARCH == "web_search"
    assert Intent.HA_ACTION == "ha_action"
