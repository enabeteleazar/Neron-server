"""Les civilites ne doivent pas mobiliser un modele de langage.

La cascade de mots-cles reconnaissait deja greeting / thanks / goodbye /
status_smalltalk, mais AUCUNE branche de l'orchestrateur ne les traitait :
ils tombaient dans le `else` final, donc sur le provider LLM.

Mesure du 03/09/2026, en production : 67 s pour repondre « Bonjour »
(`{"selected_route": "llm_provider", "intent": "greeting"}` dans les logs).

Avant cela, le defaut etait masque : le detecteur timer captait « bon-jour »
par correspondance de sous-chaine et repondait la date. Corriger ce premier
defaut a rendu le second visible.
"""

from __future__ import annotations

import pytest

from core.pipeline.intent.intent_router import Intent
from core.pipeline.orchestrator import CoreOrchestrator, _SMALLTALK_REPLIES


@pytest.fixture(scope="module")
def orchestrator():
    """Une seule instance : le constructeur charge CamemBERT (~30 s)."""
    return CoreOrchestrator()


@pytest.mark.parametrize(
    "query, expected_intent",
    [
        ("Bonjour", Intent.GREETING),
        ("Salut Neron", Intent.GREETING),
        ("Merci", Intent.THANKS),
        ("Au revoir", Intent.GOODBYE),
        ("Comment vas-tu", Intent.STATUS_SMALLTALK),
    ],
)
async def test_civilities_are_answered_locally(orchestrator, query, expected_intent):
    decision, _ = await orchestrator.decide(query)

    assert decision.selected_route == "smalltalk", (
        f"{query!r} doit rester local, obtenu : {decision.selected_route}"
    )
    assert decision.intent == expected_intent.value


async def test_smalltalk_execution_returns_a_reply_without_llm(orchestrator):
    decision, _ = await orchestrator.decide("Bonjour")
    response, executor, metadata = orchestrator._execute_smalltalk(decision)

    assert response.strip()
    assert executor == "smalltalk_module"
    assert metadata["llm_used"] is False


@pytest.mark.parametrize(
    "query",
    ["Quel est ton statut ?", "Statut systeme", "Quel est l etat du systeme"],
)
async def test_real_status_requests_still_reach_status_provider(orchestrator, query):
    """Garde-fou du reordonnancement.

    La branche civilite a ete placee AVANT la branche status, parce que
    `detect_status_intent` captait « comment vas-tu » comme `health_query` et
    y repondait par un rapport technique. Une demande d'etat EXPLICITE doit
    continuer d'atteindre status_provider.
    """
    decision, _ = await orchestrator.decide(query)

    assert decision.selected_route != "smalltalk", (
        f"{query!r} est une vraie demande d'etat, pas une civilite"
    )


def test_every_smalltalk_intent_has_a_reply():
    for intent in (
        Intent.GREETING,
        Intent.THANKS,
        Intent.GOODBYE,
        Intent.STATUS_SMALLTALK,
    ):
        assert _SMALLTALK_REPLIES.get(intent, "").strip(), intent
