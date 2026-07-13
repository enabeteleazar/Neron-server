from __future__ import annotations

import pytest

from core.modules.identity import detect_identity_intent
from core.modules.timer import detect_timer_intent
from core.pipeline.intent.intent_router import Intent, IntentRouter
from core.pipeline.nlp.french_normalizer import normalize_text
from core.pipeline.orchestrator import CoreOrchestrator


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Qui es tu ?", "qui es tu"),
        ("Qui est tu ?", "qui es tu"),
        ("Tu est qui ?", "tu es qui"),
        ("  QUI   ES-TU  ? ", "qui es tu"),
        ("C'est quoi ton nom ?", "quel est ton nom"),
        ("Présente-toi", "presente toi"),
        ("Quelle heure il est ?", "quelle heure il est"),
        ("Quel heure est il ?", "quelle heure est il"),
        ("Donne-moi l'heure", "donne moi l heure"),
        ("Euh, qui est tu ?", "qui es tu"),
        ("Lance le services", "lance le service"),
        ("Démarre le service", "lance le service"),
    ],
)
def test_french_normalizer_canonical_forms(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    "query",
    [
        "Qui es tu ?",
        "Qui est tu ?",
        "Tu est qui ?",
        "C'est quoi ton nom ?",
        "Présente toi",
        "Euh qui est tu",
    ],
)
def test_identity_detector_accepts_french_variants(query: str) -> None:
    result = detect_identity_intent(query)
    assert result["matched"] is True
    assert result["kind"] == "identity_short"


@pytest.mark.parametrize(
    "query",
    [
        "Quelle heure il est ?",
        "Quel heure est il ?",
        "Donne moi l'heure",
    ],
)
def test_timer_detector_accepts_french_variants(query: str) -> None:
    result = detect_timer_intent(query)
    assert result["matched"] is True
    assert result["kind"] == "time"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "Qui es tu ?",
        "Qui est tu ?",
        "Tu est qui ?",
        "C'est quoi ton nom ?",
        "Présente toi",
    ],
)
async def test_intent_router_maps_identity_variants_to_same_intent(query: str) -> None:
    result = await IntentRouter().route(query)
    assert result.intent == Intent.IDENTITY_QUERY


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "Qui est tu ?",
        "Tu est qui ?",
        "C'est quoi ton nom ?",
        "Quel heure est il ?",
    ],
)
async def test_orchestrator_uses_normalized_text_before_routing(query: str) -> None:
    decision, _ = await CoreOrchestrator().decide(query)
    assert decision.selected_route in {"identity_provider", "timer_engine"}
