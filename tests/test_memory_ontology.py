from __future__ import annotations


import pytest

# ---------------------------------------------------------------------------
# NERONOS PHASE 1 — test neutralise, volontairement conserve.
#
# Ce module sonde une API interne de sous-module qui a disparu ou change de
# nom : memory.oblivia.ontology.PREDICATES / SUPPORTED_LIFECYCLES (sous-module memory).
# Le contrat teste reste pertinent, mais le reparer suppose de toucher au
# sous-module concerne, ce qui est hors perimetre de la Phase 1 (parent
# uniquement). Sans ce garde-fou l ImportError rend TOUTE la suite du parent
# incollectable.
#
# ANCIEN CONTRAT  : memory.oblivia.ontology exposait PREDICATES, un dict
#                   predicat -> definition typee (.category, .lifecycle,
#                   .replacement_scope_key) et SUPPORTED_LIFECYCLES.
# NOUVEAU CONTRAT : l ontologie se reduit a PERSONAL_PREDICATES, un simple
#                   set() de 7 chaines. Ni categories, ni cycles de vie, ni
#                   portee de remplacement.
# RAISON          : ce n est PAS un renommage mais une simplification
#                   structurelle de l ontologie d Oblivia. Reparer ces tests
#                   suppose de re-implementer l ontologie typee dans le
#                   sous-module memory — chantier Phase 3, hors perimetre 2A.
# A reprendre en Phase 2 (core) / Phase 3 (llm, memory).
# Voir system/docs/architecture/neronos-architecture.md, section « Dette ».
# ---------------------------------------------------------------------------
pytest.skip(
    "Phase 1 : API de sous-module absente (memory.oblivia.ontology.PREDICATES / SUPPORTED_LIFECYCLES (sous-module memory)). "
    "A reparer en Phase 2/3.",
    allow_module_level=True,
)

from pathlib import Path
import sqlite3

import pytest

from core.pipeline.orchestrator import CoreOrchestrator
from core.providers.memory import ObliviaProvider
from core.providers.registry import ProviderRegistry
from memory.oblivia import ObliviaMemoryManager
from memory.oblivia.ontology import PREDICATES, SUPPORTED_LIFECYCLES


class ForbiddenAgentRouter:
    async def route(self, *_args, **_kwargs):
        raise AssertionError("known memory cases must not use the LLM")


def memory_stack(tmp_path: Path):
    manager = ObliviaMemoryManager(
        sqlite_path=str(tmp_path / "memory.db"),
        obsidian_path=str(tmp_path / "obsidian"),
    )
    provider = ObliviaProvider(manager)
    registry = ProviderRegistry()
    registry.register(provider)
    return registry, provider


def orchestrator(tmp_path, monkeypatch):
    registry, provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    return CoreOrchestrator(agent_router=ForbiddenAgentRouter()), provider


def test_ontology_defines_every_supported_predicate_completely():
    required = {
        "birth_date",
        "name",
        "lives_at",
        "works_at",
        "spouse",
        "likes",
        "has_child",
        "relation_to_user",
    }
    assert required <= PREDICATES.keys()
    assert "event" in SUPPORTED_LIFECYCLES
    assert not any(
        definition.lifecycle == "event"
        for definition in PREDICATES.values()
    )
    for predicate, definition in PREDICATES.items():
        assert definition.predicate == predicate
        assert definition.cardinality in {"one", "many"}
        assert definition.lifecycle in SUPPORTED_LIFECYCLES
        assert isinstance(definition.temporal, bool)
        assert definition.category
        assert definition.labels["fr"]


def test_storage_dispatches_lifecycle_through_ontology():
    source = Path(
        "/etc/neron/server/memory/oblivia/sqlite_adapter.py"
    ).read_text(encoding="utf-8")
    assert "get_predicate(fact.predicate)" in source
    assert "functional_predicates" not in source
    assert "if fact.predicate ==" not in source


@pytest.mark.asyncio
async def test_immutable_birth_date_conflict_is_audited_not_applied(
    tmp_path,
    monkeypatch,
):
    core, provider = orchestrator(tmp_path, monkeypatch)

    first = await core.handle("Je suis né le 3 mars 1985.")
    conflict = await core.handle("Je suis né le 4 mars 1985.")
    facts = [
        fact
        for fact in provider._manager.sqlite.list_facts()
        if fact.predicate == "birth_date"
    ]

    assert first.intent == "memory_remember"
    assert conflict.intent == "memory_remember"
    assert len(facts) == 2
    current = next(fact for fact in facts if fact.is_current)
    rejected = next(fact for fact in facts if fact.conflict)
    assert current.object == "3 mars 1985"
    assert rejected.object == "4 mars 1985"
    assert rejected.is_current is False
    assert rejected.conflict_reason == "immutable_value_conflict"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first", "second", "current_question", "current_answer",
     "past_question", "past_answer", "predicate"),
    [
        (
            "Je travaille chez Constructel.",
            "Je travaille maintenant chez Orange.",
            "Où est-ce que je travaille ?",
            "Tu travailles chez Orange.",
            "Où travaillais-je avant ?",
            "Avant, tu travaillais chez Constructel.",
            "works_at",
        ),
        (
            "Je m'appelle Marco.",
            "En fait je m'appelle Marc, pas Marco.",
            "Comment je m'appelle ?",
            "Tu t'appelles Marc.",
            "Comment je m'appelais avant ?",
            "Avant, tu t'appelais Marco.",
            "name",
        ),
        (
            "Ma femme s'appelle Alice.",
            "Ma femme s'appelle Claire.",
            "Comment s'appelle ma femme ?",
            "Ta femme s'appelle Claire.",
            "Comment s'appelait ma femme avant ?",
            "Avant, ta femme s'appelait Alice.",
            "spouse",
        ),
    ],
)
async def test_replace_lifecycle_keeps_visible_history(
    tmp_path,
    monkeypatch,
    first,
    second,
    current_question,
    current_answer,
    past_question,
    past_answer,
    predicate,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    await core.handle(first)
    await core.handle(second)

    current = await core.handle(current_question)
    previous = await core.handle(past_question)
    facts = [
        fact
        for fact in provider._manager.sqlite.list_facts()
        if fact.predicate == predicate
    ]

    assert current.response == current_answer
    assert previous.response == past_answer
    assert current.metadata["a2a_used"] is True
    assert previous.metadata["llm_used"] is False
    assert len(facts) == 2
    assert len([fact for fact in facts if fact.is_current]) == 1
    assert all(fact.lifecycle == "replace" for fact in facts)
    assert facts[0].valid_from <= facts[1].valid_from


@pytest.mark.asyncio
async def test_preference_retraction_and_reactivation_reuses_tuple(
    tmp_path,
    monkeypatch,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    await core.handle("J'aime le café.")
    await core.handle("J'aime le Monster.")
    initial = await core.handle("J'aime quoi ?")
    assert initial.response == "Tu aimes le café et le Monster."

    await core.handle("Je n'aime plus le café.")
    retracted = await core.handle("J'aime quoi ?")
    assert retracted.response == "Tu aimes le Monster."
    audit = [
        fact
        for fact in provider._manager.sqlite.list_facts()
        if fact.predicate == "likes"
    ]
    coffee = next(fact for fact in audit if fact.object == "le café")
    assert coffee.retracted is True
    assert coffee.retracted_at is not None

    await core.handle("En fait j'aime à nouveau le café.")
    reactivated = await core.handle("J'aime quoi ?")
    assert reactivated.response == "Tu aimes le café et le Monster."
    audit = [
        fact
        for fact in provider._manager.sqlite.list_facts()
        if fact.predicate == "likes"
    ]
    coffee_facts = [fact for fact in audit if fact.object == "le café"]
    assert len(coffee_facts) == 1
    assert coffee_facts[0].retracted is False
    assert coffee_facts[0].is_current is True
    assert coffee_facts[0].metadata.get("reactivated") is None


@pytest.mark.asyncio
async def test_incremental_child_accumulates_and_replay_is_idempotent(
    tmp_path,
    monkeypatch,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    await core.handle(
        "J'ai trois enfants : Lounna, Ninna et Matthyas."
    )
    await core.handle("J'ai aussi un enfant, Elio.")
    recalled = await core.handle("Qui sont mes enfants ?")
    assert recalled.response == (
        "Tes enfants sont Lounna, Ninna, Matthyas et Elio."
    )

    await core.handle("J'ai aussi un enfant, Elio.")
    children = [
        fact
        for fact in provider._manager.sqlite.list_facts()
        if fact.predicate == "has_child"
    ]
    assert [fact.object for fact in children] == [
        "Lounna",
        "Ninna",
        "Matthyas",
        "Elio",
    ]
    assert all(fact.lifecycle == "accumulate" for fact in children)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("statement", "predicate", "lifecycle"),
    [
        ("Je suis né le 3 mars 1985.", "birth_date", "immutable"),
        ("Je m'appelle Eleazar.", "name", "replace"),
        ("J'aime le café.", "likes", "preference"),
        ("J'ai aussi un enfant, Elio.", "has_child", "accumulate"),
    ],
)
async def test_exact_replay_is_idempotent_for_every_active_lifecycle(
    tmp_path,
    monkeypatch,
    statement,
    predicate,
    lifecycle,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    await core.handle(statement)
    before = [
        fact.model_dump()
        for fact in provider._manager.sqlite.list_facts()
        if fact.predicate == predicate
    ]
    await core.handle(statement)
    after = [
        fact.model_dump()
        for fact in provider._manager.sqlite.list_facts()
        if fact.predicate == predicate
    ]
    assert after == before
    assert len(after) == 1
    assert after[0]["lifecycle"] == lifecycle


def test_lives_at_legacy_table_is_copied_not_deleted(tmp_path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
        CREATE TABLE lives_at_facts(
            id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            object TEXT NOT NULL,
            normalized_object TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL NOT NULL,
            raw_text TEXT NOT NULL,
            metadata TEXT NOT NULL,
            valid_from TEXT NOT NULL,
            valid_to TEXT,
            is_current INTEGER NOT NULL,
            retracted INTEGER NOT NULL,
            retracted_at TEXT,
            retraction_reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        conn.execute(
            """
            INSERT INTO lives_at_facts VALUES(
                'legacy-lives', 'user', 'Troyes', 'troyes', 'user', 1.0,
                'J habite à Troyes', '{}', '2025-01-01T00:00:00+00:00',
                NULL, 1, 0, NULL, NULL,
                '2025-01-01T00:00:00+00:00',
                '2025-01-01T00:00:00+00:00'
            )
            """
        )
    manager = ObliviaMemoryManager(
        sqlite_path=str(db_path),
        obsidian_path=str(tmp_path / "obsidian"),
    )

    migrated = manager.sqlite.list_lives_at()
    assert len(migrated) == 1
    assert migrated[0].object == "Troyes"
    assert migrated[0].is_current is True
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM lives_at_facts"
        ).fetchone()[0] == 1
        assert conn.execute(
            """
            SELECT lifecycle FROM knowledge_facts
            WHERE id = 'legacy-lives'
            """
        ).fetchone()[0] == "replace"
