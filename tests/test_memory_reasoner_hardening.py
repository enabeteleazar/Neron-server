from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.memory import detect_memory_intent
from core.pipeline.intent.intent_router import Intent, IntentRouter
from core.pipeline.orchestrator import CoreOrchestrator
from core.providers.memory import ObliviaProvider
from core.providers.registry import ProviderRegistry
from tests._memory_stack import memory_stack
from memory.oblivia import MemoryRecord


QUESTIONS = [
    "Quels anciens souvenirs possèdes-tu ?",
    "Quelles informations ne sont plus actuelles ?",
    "Quelles informations sont obsolètes ?",
    "Montre-moi tout ce que tu sais.",
    "Montre toute ma mémoire.",
    "Quels souvenirs possèdes-tu ?",
    "Combien de souvenirs as-tu sur moi ?",
    "Quels types d'informations connais-tu ?",
    "Quels prédicats connais-tu sur moi ?",
    "Ai-je des informations contradictoires ?",
    "As-tu détecté des conflits ?",
    "Y a-t-il des souvenirs rétractés ?",
    "As-tu des informations douteuses ?",
    "Y a-t-il des données obsolètes ?",
    "Qui habite avec moi ?",
    "Qui dépend de moi ?",
    "Qui fait partie de mon foyer ?",
    "Si je déménage, qui déménage probablement avec moi ?",
    "Qui est lié à moi ?",
    "Qui fait partie de ma famille ?",
    "Qui partage ma vie ?",
    "Tu me connais bien ?",
    "Est-ce que tu te souviens de moi ?",
    "As-tu appris des choses sur moi ?",
    "Qu’est-ce que tu retiens principalement de moi ?",
    "Qu’est-ce qui me caractérise ?",
    "Que pourrais-tu raconter sur moi à quelqu’un ?",
    "Si tu devais me présenter, que dirais-tu ?",
    "Quelle est la dernière chose importante que tu as apprise sur moi ?",
]


class ForbiddenAgentRouter:
    async def route(self, *_args, **_kwargs):
        raise AssertionError("known memory questions must not use the LLM")


def orchestrator(tmp_path: Path, monkeypatch):
    registry, provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    return CoreOrchestrator(agent_router=ForbiddenAgentRouter()), provider


@pytest.mark.parametrize("question", QUESTIONS)
def test_hardening_questions_are_memory_recall(question):
    detected = detect_memory_intent(question)
    assert detected["matched"] is True
    assert detected["kind"] == "recall"


def test_profile_recall_is_not_misclassified_as_remember():
    detected = detect_memory_intent(
        "Qu’est-ce que tu retiens principalement de moi ?"
    )
    assert detected["kind"] == "recall"


@pytest.mark.asyncio
async def test_latest_personal_fact_is_never_home_assistant():
    result = await IntentRouter().route(
        "Quelle est la dernière chose importante que tu as apprise sur moi ?"
    )
    assert result.intent != Intent.HA_ACTION


async def seed(core: CoreOrchestrator):
    for statement in (
        "Je m'appelle Eleazar.",
        "J'habite à Saron-sur-Aube.",
        "J'habite maintenant à Troyes.",
        "Je travaille chez Constructel.",
        "Je travaille maintenant chez Orange.",
        "Ma femme s'appelle Alice.",
        "J'ai trois enfants : Lounna, Ninna et Matthyas.",
        "J'aime le café.",
        "J'aime le Monster.",
        "Je n'aime plus le café.",
        "Je suis né le 3 mars 1985.",
        "Je suis né le 4 mars 1985.",
    ):
        await core.handle(statement)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    [
        "Tu me connais bien ?",
        "Est-ce que tu te souviens de moi ?",
        "As-tu appris des choses sur moi ?",
        "Qu’est-ce que tu retiens principalement de moi ?",
        "Qu’est-ce qui me caractérise ?",
        "Que pourrais-tu raconter sur moi à quelqu’un ?",
        "Si tu devais me présenter, que dirais-tu ?",
    ],
)
async def test_natural_profile_questions_use_user_facts_only(
    tmp_path,
    monkeypatch,
    question,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    await seed(core)
    provider._manager.remember(
        MemoryRecord(
            category="project",
            content="SECRET_PROJET architecture interne Néron.",
        )
    )

    result = await core.handle(question)

    assert "Eleazar" in result.response
    assert "Troyes" in result.response
    assert "Alice" in result.response
    assert "SECRET_PROJET" not in result.response
    assert result.intent == "memory_recall"
    assert result.executor == "oblivia-memory"
    assert result.metadata["a2a_used"] is True
    assert result.metadata["llm_used"] is False


@pytest.mark.asyncio
async def test_memory_audit_predicates_categories_and_count_without_project(
    tmp_path,
    monkeypatch,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    await seed(core)
    provider._manager.remember(
        MemoryRecord(category="project", content="SECRET_PROJET")
    )

    audit = await core.handle("Montre toute ma mémoire.")
    count = await core.handle("Combien de souvenirs as-tu sur moi ?")
    predicates = await core.handle("Quels prédicats connais-tu sur moi ?")
    categories = await core.handle(
        "Quels types d'informations connais-tu ?"
    )

    assert "Mémoire personnelle" in audit.response
    assert "SECRET_PROJET" not in audit.response
    assert "faits structurés sur toi" in count.response
    assert "lives_at" in predicates.response
    assert "works_at" in predicates.response
    assert "location" in categories.response
    assert all(
        result.metadata["llm_used"] is False
        for result in (audit, count, predicates, categories)
    )


@pytest.mark.asyncio
async def test_stale_retracted_and_conflict_audit(tmp_path, monkeypatch):
    core, _provider = orchestrator(tmp_path, monkeypatch)
    await seed(core)

    stale = await core.handle(
        "Quelles informations ne sont plus actuelles ?"
    )
    retracted = await core.handle(
        "Y a-t-il des souvenirs rétractés ?"
    )
    conflicts = await core.handle("As-tu détecté des conflits ?")

    assert "Saron-sur-Aube" in stale.response
    assert "Constructel" in stale.response
    assert "le café" in retracted.response
    assert "4 mars 1985" in conflicts.response
    assert stale.metadata["llm_used"] is False
    assert retracted.metadata["llm_used"] is False
    assert conflicts.metadata["llm_used"] is False


@pytest.mark.asyncio
async def test_family_household_dependency_and_moving_are_prudent(
    tmp_path,
    monkeypatch,
):
    core, _provider = orchestrator(tmp_path, monkeypatch)
    await seed(core)

    family = await core.handle("Qui fait partie de ma famille ?")
    linked = await core.handle("Qui est lié à moi ?")
    depends = await core.handle("Qui dépend de moi ?")
    household = await core.handle("Qui habite avec moi ?")
    moving = await core.handle(
        "Si je déménage, qui déménage probablement avec moi ?"
    )

    for result in (family, linked):
        assert "Alice" in result.response
        assert "Lounna" in result.response
        assert "Matthyas" in result.response
    assert "trois enfants" in depends.response
    assert "administrativement ou financièrement" in depends.response
    assert "Je ne sais pas précisément qui habite avec toi" in household.response
    assert "je ne sais pas encore qui vit officiellement" in moving.response
    assert all(
        result.metadata["llm_used"] is False
        for result in (family, linked, depends, household, moving)
    )


@pytest.mark.asyncio
async def test_latest_fact_excludes_project_and_routes_via_a2a(
    tmp_path,
    monkeypatch,
):
    core, provider = orchestrator(tmp_path, monkeypatch)
    await core.handle("Je m'appelle Eleazar.")
    await core.handle("Je travaille chez Constructel.")
    provider._manager.remember(
        MemoryRecord(
            category="project",
            content="SECRET_PROJET dernière trace technique",
        )
    )

    result = await core.handle(
        "Quelle est la dernière chose importante que tu as apprise sur moi ?"
    )

    assert "emploi : Constructel" in result.response
    assert "SECRET_PROJET" not in result.response
    assert result.intent == "memory_recall"
    assert result.executor == "oblivia-memory"
    assert result.metadata["a2a_used"] is True
    assert result.metadata["llm_used"] is False
