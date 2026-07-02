from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.memory import detect_memory_intent
from core.pipeline.orchestrator import CoreOrchestrator
from core.providers.memory import ObliviaProvider
from core.providers.registry import ProviderRegistry
from memory.oblivia import ObliviaMemoryManager
from memory.oblivia.ontology import PREDICATES
from memory.oblivia.predicate_discovery import PredicateDiscovery


class ForbiddenAgentRouter:
    async def route(self, *_args, **_kwargs):
        raise AssertionError("known possession memory must not use the LLM")


def orchestrator(tmp_path: Path, monkeypatch):
    manager = ObliviaMemoryManager(
        sqlite_path=str(tmp_path / "memory.db"),
        obsidian_path=str(tmp_path / "obsidian"),
    )
    provider = ObliviaProvider(manager)
    registry = ProviderRegistry()
    registry.register(provider)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    return CoreOrchestrator(agent_router=ForbiddenAgentRouter()), provider


def test_device_purchase_predicates_are_declared_in_ontology():
    expected = {
        "owns_device": "devices",
        "owns_vehicle": "ownership",
        "owns_object": "possessions",
        "purchased": "purchases",
        "uses_device": "devices",
    }
    for predicate, category in expected.items():
        assert PREDICATES[predicate].category == category
    assert PREDICATES["owns_device"].replacement_scope_key == "device_slot"
    assert PREDICATES["purchased"].lifecycle == "accumulate"


def test_discovery_maps_near_predicates_and_proposes_clear_candidates():
    discovery = PredicateDiscovery()
    mapped = discovery.discover("téléphone")
    candidate = discovery.discover("collectionne figurine")
    ambiguous = discovery.discover("")

    assert mapped.predicate == "owns_device"
    assert mapped.status == "mapped"
    assert candidate.status == "candidate"
    assert candidate.predicate in discovery.candidates
    assert ambiguous.requires_confirmation is True


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("J’ai acheté l’iPhone 16.", "remember"),
        ("J’ai un iPhone 16.", "remember"),
        ("Je possède un iPhone 16.", "remember"),
        ("J’utilise l’iPhone 16.", "remember"),
        ("Mon téléphone est l’iPhone 16.", "remember"),
        ("Mon ordinateur est un MacBook Pro.", "remember"),
        ("Quel est mon téléphone ?", "recall"),
        ("Quel téléphone j’utilise ?", "recall"),
        ("Quel smartphone ai-je ?", "recall"),
        ("Quels appareils je possède ?", "recall"),
        ("Qu’est-ce que j’ai acheté ?", "recall"),
        ("Tu te souviens de mon téléphone ?", "recall"),
    ],
)
def test_device_memory_intents_are_detected(text, kind):
    detected = detect_memory_intent(text)
    assert detected["matched"] is True
    assert detected["kind"] == kind


@pytest.mark.asyncio
async def test_iphone_purchase_is_structured_and_recallable_without_llm(
    tmp_path,
    monkeypatch,
):
    core, provider = orchestrator(tmp_path, monkeypatch)

    remembered = await core.handle(
        "J’ai acheté l’iPhone 16, il est très bien."
    )
    phone = await core.handle("Quel est mon téléphone ?")
    devices = await core.handle("Quels appareils je possède ?")
    purchases = await core.handle("Qu’est-ce que j’ai acheté ?")

    assert remembered.intent == "memory_remember"
    assert remembered.executor == "oblivia"
    assert remembered.metadata["a2a_used"] is True
    assert remembered.metadata["llm_used"] is False
    assert phone.response == "Ton téléphone est un iPhone 16."
    assert devices.response == "Tu possèdes un iPhone 16."
    assert purchases.response == "Tu as acheté un iPhone 16."
    assert all(
        result.metadata["a2a_used"] is True
        and result.metadata["llm_used"] is False
        for result in (phone, devices, purchases)
    )

    facts = provider._manager.sqlite.list_facts()
    triples = {
        (fact.subject, fact.predicate, fact.object)
        for fact in facts
    }
    assert ("user", "owns_device", "iPhone 16") in triples
    assert ("user", "purchased", "iPhone 16") in triples
    assert ("iPhone 16", "type", "smartphone") in triples
    assert ("iPhone 16", "brand", "Apple") in triples
    assert ("iPhone 16", "acquired_by", "purchase") in triples


@pytest.mark.asyncio
async def test_replayed_purchase_is_idempotent(tmp_path, monkeypatch):
    core, provider = orchestrator(tmp_path, monkeypatch)
    statement = "J’ai acheté l’iPhone 16."
    await core.handle(statement)
    before = [
        fact.model_dump()
        for fact in provider._manager.sqlite.list_facts()
    ]
    await core.handle(statement)
    after = [
        fact.model_dump()
        for fact in provider._manager.sqlite.list_facts()
    ]
    assert after == before
    assert len(
        [
            fact
            for fact in provider._manager.sqlite.list_facts()
            if fact.predicate == "purchased"
            and fact.object == "iPhone 16"
        ]
    ) == 1


@pytest.mark.asyncio
async def test_phone_slot_replaces_phone_but_keeps_other_devices(
    tmp_path,
    monkeypatch,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    await core.handle("Mon téléphone est l’iPhone 15.")
    await core.handle("Mon ordinateur est un MacBook Pro.")
    await core.handle("Mon téléphone est l’iPhone 16.")

    phone = await core.handle("Quel est mon téléphone ?")
    devices = await core.handle("Quels appareils je possède ?")
    facts = [
        fact
        for fact in provider._manager.sqlite.list_facts()
        if fact.predicate == "owns_device"
    ]

    assert phone.response == "Ton téléphone est un iPhone 16."
    assert "iPhone 16" in devices.response
    assert "MacBook Pro" in devices.response
    assert "iPhone 15" not in devices.response
    assert len(facts) == 3
    assert next(f for f in facts if f.object == "iPhone 15").is_current is False

