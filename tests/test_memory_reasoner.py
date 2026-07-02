from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.memory import detect_memory_intent
from core.pipeline.orchestrator import CoreOrchestrator
from core.providers.memory import ObliviaProvider
from core.providers.registry import ProviderRegistry
from memory.oblivia import ObliviaMemoryManager
from memory.oblivia import MemoryRecord


class ForbiddenAgentRouter:
    async def route(self, *_args, **_kwargs):
        raise AssertionError("memory reasoner cases must not use the LLM")


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


@pytest.mark.parametrize(
    "question",
    [
        "Qui suis-je ?",
        "Parle-moi de moi.",
        "Présente-moi.",
        "Que sais-tu de moi ?",
        "Fais un résumé de ce que tu sais sur moi.",
        "Qui est ma femme ?",
        "Qui est mon épouse ?",
        "Où ai-je travaillé ?",
        "Où travaillais-je avant ?",
        "Qu’est-ce que j’aime ?",
        "J’aime quoi ?",
        "Qu’est-ce que j’aimais avant ?",
    ],
)
def test_reasoner_questions_are_detected_as_memory_recall(question):
    detected = detect_memory_intent(question)
    assert detected["matched"] is True
    assert detected["kind"] == "recall"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    [
        "Qui suis-je ?",
        "Parle-moi de moi.",
        "Présente-moi.",
        "Que sais-tu de moi ?",
        "Fais un résumé de ce que tu sais sur moi.",
    ],
)
async def test_user_profile_synthesis_routes_to_oblivia_without_llm(
    tmp_path,
    monkeypatch,
    question,
):
    core, _provider = orchestrator(tmp_path, monkeypatch)
    for statement in (
        "Je m'appelle Eleazar.",
        "J'habite à Troyes.",
        "Je travaille chez Constructel.",
        "Ma femme s'appelle Alice.",
        "J'ai trois enfants : Lounna, Ninna et Matthyas.",
        "J'aime le café.",
        "J'aime le Monster.",
    ):
        await core.handle(statement)

    result = await core.handle(question)

    assert result.response == (
        "Tu t'appelles Eleazar. "
        "Tu habites actuellement à Troyes. "
        "Tu travailles chez Constructel. "
        "Ta femme s'appelle Alice. "
        "Tu as trois enfants : Lounna, Ninna et Matthyas. "
        "Tu aimes le café et le Monster."
    )
    assert result.intent == "memory_recall"
    assert result.executor == "oblivia"
    assert result.metadata["selected_route"] == "memory_provider"
    assert result.metadata["memory_action"] == "recall"
    assert result.metadata["a2a_used"] is True
    assert result.metadata["llm_used"] is False


@pytest.mark.asyncio
async def test_profile_with_no_user_facts_is_clean_and_ignores_project_memory(
    tmp_path,
    monkeypatch,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    provider._manager.remember(
        MemoryRecord(
            category="project",
            content="Néron utilise une architecture technique interne.",
        )
    )

    result = await core.handle("Que sais-tu de moi ?")

    assert result.response == "Je connais encore peu d’informations sur toi."
    assert "architecture" not in result.response
    assert result.metadata["llm_used"] is False
    assert result.metadata["memory_facts"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("question", ["Qui est ma femme ?", "Qui est mon épouse ?"])
async def test_spouse_semantic_alias(question, tmp_path, monkeypatch):
    core, _provider = orchestrator(tmp_path, monkeypatch)
    await core.handle("Ma femme s'appelle Alice.")

    result = await core.handle(question)

    assert result.response == "Ta femme s'appelle Alice."
    assert result.executor == "oblivia"
    assert result.metadata["a2a_used"] is True
    assert result.metadata["llm_used"] is False


@pytest.mark.asyncio
async def test_works_at_full_history_is_chronological(
    tmp_path,
    monkeypatch,
):
    core, _provider = orchestrator(tmp_path, monkeypatch)
    await core.handle("Je travaille chez Constructel.")
    await core.handle("Je travaille maintenant chez Orange.")

    current = await core.handle("Où est-ce que je travaille ?")
    previous = await core.handle("Où travaillais-je avant ?")
    history = await core.handle("Où ai-je travaillé ?")

    assert current.response == "Tu travailles chez Orange."
    assert previous.response == "Avant, tu travaillais chez Constructel."
    assert history.response == (
        "Tu as travaillé chez Constructel, puis chez Orange."
    )
    assert history.metadata["llm_used"] is False


@pytest.mark.asyncio
async def test_works_at_history_is_unique_but_audit_keeps_cycles(
    tmp_path,
    monkeypatch,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    for statement in (
        "Je travaille chez Constructel.",
        "Je travaille maintenant chez Orange.",
        "Je travaille chez Constructel.",
        "Je travaille maintenant chez Orange.",
    ):
        await core.handle(statement)

    history = await core.handle("Où ai-je travaillé ?")
    audit = [
        fact
        for fact in provider._manager.sqlite.list_facts()
        if fact.predicate == "works_at"
    ]

    assert history.response == (
        "Tu as travaillé chez Constructel, puis chez Orange."
    )
    assert [fact.object for fact in audit] == [
        "Constructel",
        "Orange",
        "Constructel",
        "Orange",
    ]


@pytest.mark.asyncio
async def test_active_and_previous_preferences_are_separated(
    tmp_path,
    monkeypatch,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    await core.handle("J'aime le café.")
    await core.handle("J'aime le Monster.")
    await core.handle("Je n'aime plus le café.")

    active = await core.handle("Qu'est-ce que j'aime ?")
    previous = await core.handle("Qu'est-ce que j'aimais avant ?")

    assert active.response == "Tu aimes le Monster."
    assert previous.response == "Avant, tu aimais le café."
    assert active.metadata["llm_used"] is False
    assert previous.metadata["llm_used"] is False
    audit = [
        fact
        for fact in provider._manager.sqlite.list_facts()
        if fact.predicate == "likes"
    ]
    assert any(fact.object == "le café" and fact.retracted for fact in audit)
