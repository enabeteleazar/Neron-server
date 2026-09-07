from __future__ import annotations

from pathlib import Path

import pytest

from core.a2a import A2AClient
from core.modules.memory import detect_memory_intent
from core.pipeline.orchestrator import CoreOrchestrator
from core.providers.memory import ObliviaProvider
from core.providers.models import ProviderRequest
from core.providers.registry import ProviderRegistry
from tests._memory_stack import memory_stack


class ForbiddenAgentRouter:
    async def route(self, *_args, **_kwargs):
        raise AssertionError("cognitive memory must not use the LLM")




@pytest.mark.parametrize(
    "statement",
    [
        "Je suis papa.",
        "Je m’appelle Eleazar.",
        "Ma femme s’appelle Alice.",
        "Mon fils s’appelle Lucas.",
        "J’habite à Saron-sur-Aube.",
        "J’aime le café.",
        "Je travaille chez Constructel.",
    ],
)
def test_explicit_personal_fact_is_detected_as_memory_remember(statement):
    detected = detect_memory_intent(statement)

    assert detected["matched"] is True
    assert detected["kind"] == "remember"
    assert detected["confidence"] == 0.95


@pytest.mark.parametrize(
    "question",
    [
        "Comment je m’appelle ?",
        "Qui est mon fils ?",
        "Où est-ce que j’habite ?",
        "Où est-ce que je travaille ?",
    ],
)
def test_personal_question_is_detected_as_memory_recall(question):
    detected = detect_memory_intent(question)

    assert detected["matched"] is True
    assert detected["kind"] == "recall"
    assert detected["confidence"] == 0.9


@pytest.mark.parametrize(
    "question",
    [
        "Où est-ce que j'habitais avant ?",
        "Où habitais-je avant ?",
        "Où ai-je vécu ?",
        "Dans quelles villes ai-je vécu ?",
    ],
)
def test_temporal_residence_question_is_detected_as_memory_recall(question):
    detected = detect_memory_intent(question)

    assert detected["matched"] is True
    assert detected["kind"] == "recall"


@pytest.mark.parametrize(
    "statement",
    [
        "J’ai habité à Laz il y a 4 ans.",
        "J’habitais à Laz avant.",
        "Avant, j’habitais à Laz.",
        "Je n’ai jamais habité à Troyes.",
        "Je n’habitais pas à Troyes.",
        "Ce n’est pas vrai, je n’ai jamais habité à Troyes.",
    ],
)
def test_temporal_correction_is_detected_as_memory_remember(statement):
    detected = detect_memory_intent(statement)

    assert detected["matched"] is True
    assert detected["kind"] == "remember"


@pytest.mark.parametrize(
    "statement",
    [
        "J'ai trois enfants : Lounna, Ninna et Matthyas.",
        "J’ai 3 enfants : Lounna, Ninna et Matthyas.",
        "Mes enfants s'appellent Lounna, Ninna et Matthyas.",
        "Mes enfants sont Lounna, Ninna et Matthyas.",
    ],
)
def test_children_collection_is_detected_as_memory_remember(statement):
    detected = detect_memory_intent(statement)

    assert detected["matched"] is True
    assert detected["kind"] == "remember"


@pytest.mark.parametrize(
    "question",
    [
        "Combien ai-je d'enfants ?",
        "Comment s'appellent mes enfants ?",
        "Qui sont mes enfants ?",
        "Qui est Lounna ?",
        "Qui est Ninna ?",
        "Qui est Matthyas ?",
    ],
)
def test_children_question_is_detected_as_memory_recall(question):
    detected = detect_memory_intent(question)

    assert detected["matched"] is True
    assert detected["kind"] == "recall"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("statement", "expected_fact"),
    [
        ("Je suis papa.", ("user", "is", "papa")),
        ("Je m’appelle Eleazar.", ("user", "name", "Eleazar")),
        (
            "Ma femme s’appelle Alice.",
            ("user", "spouse", "Alice"),
        ),
        ("Mon fils s’appelle Lucas.", ("user.son", "name", "Lucas")),
        (
            "J’habite à Saron-sur-Aube.",
            ("user", "lives_at", "Saron-sur-Aube"),
        ),
        ("J’aime le café.", ("user", "likes", "le café")),
        (
            "Je travaille chez Constructel.",
            ("user", "works_at", "Constructel"),
        ),
    ],
)
async def test_explicit_personal_fact_routes_to_oblivia_and_is_structured(
    tmp_path,
    monkeypatch,
    statement,
    expected_fact,
):
    registry, _provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())

    response = await orchestrator.handle(statement)

    assert response.intent == "memory_remember"
    assert response.executor == "oblivia-memory"
    assert response.metadata["selected_route"] == "memory_provider"
    assert response.metadata["memory_action"] == "remember"
    assert response.metadata["a2a_used"] is True
    assert response.metadata["llm_used"] is False
    stored = _provider._manager.sqlite.list_facts(limit=1)[0]
    assert (stored.subject, stored.predicate, stored.object) == expected_fact


@pytest.mark.asyncio
async def test_memory_provider_executes_through_a2a(tmp_path):
    registry, _provider = memory_stack(tmp_path)
    client = A2AClient()

    response = await registry.execute_via_a2a(
        "oblivia-memory",
        ProviderRequest(
            action="remember",
            payload={"content": "Je suis papa."},
            trace_id="memory-trace",
        ),
        client=client,
    )

    assert response.error is None
    assert response.trace_id == "memory-trace"
    fact = response.result["metadata"]["facts"][0]
    assert fact["subject"] == "user"
    assert fact["predicate"] == "is"
    assert fact["object"] == "papa"
    assert fact["confidence"] == 1.0
    assert client.get_agent("provider:oblivia-memory") is not None


@pytest.mark.asyncio
async def test_oblivia_understands_raw_memory_directive_over_a2a(tmp_path):
    registry, _provider = memory_stack(tmp_path)

    remembered = await registry.execute_via_a2a(
        "oblivia-memory",
        ProviderRequest(
            action="remember",
            payload={"content": "Mémorise que ma femme s'appelle Alice."},
        ),
    )
    recalled = await registry.execute_via_a2a(
        "oblivia-memory",
        ProviderRequest(
            action="recall",
            payload={"query": "Comment s'appelle ma femme ?"},
        ),
    )

    assert remembered.error is None
    fact = remembered.result["metadata"]["facts"][0]
    assert (fact["subject"], fact["predicate"], fact["object"]) == (
        "user",
        "spouse",
        "Alice",
    )
    assert recalled.result["answer"] == "Ta femme s'appelle Alice."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("statement", "question", "answer"),
    [
        ("Je suis papa.", "Qui est papa ?", "Papa, c'est toi."),
        (
            "Ma femme s'appelle Alice.",
            "Comment s'appelle ma femme ?",
            "Ta femme s'appelle Alice.",
        ),
        (
            "J'aime le café.",
            "Qu'est-ce que j'aime boire ?",
            "Tu apprécies le café.",
        ),
    ],
)
async def test_structured_fact_extraction_and_natural_recall(
    tmp_path,
    monkeypatch,
    statement,
    question,
    answer,
):
    registry, _provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())

    remembered = await orchestrator.handle(statement)
    recalled = await orchestrator.handle(question)

    assert remembered.intent == "memory_remember"
    assert remembered.executor == "oblivia-memory"
    assert remembered.metadata["selected_route"] == "memory_provider"
    assert remembered.metadata["memory_action"] == "remember"
    assert remembered.metadata["a2a_used"] is True
    assert remembered.metadata["llm_used"] is False
    assert recalled.response == answer
    assert recalled.executor == "oblivia-memory"
    assert recalled.metadata["a2a_used"] is True
    assert recalled.metadata["memory_facts"]
    assert recalled.metadata["llm_used"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("statement", "question", "answer"),
    [
        (
            "Je m’appelle Eleazar.",
            "Comment je m’appelle ?",
            "Tu t'appelles Eleazar.",
        ),
        (
            "Mon fils s’appelle Lucas.",
            "Qui est mon fils ?",
            "Ton fils s'appelle Lucas.",
        ),
        (
            "J’habite à Saron-sur-Aube.",
            "Où est-ce que j’habite ?",
            "Tu habites à Saron-sur-Aube.",
        ),
        (
            "Je travaille chez Constructel.",
            "Où est-ce que je travaille ?",
            "Tu travailles chez Constructel.",
        ),
    ],
)
async def test_personal_fact_end_to_end_remember_then_recall(
    tmp_path,
    monkeypatch,
    statement,
    question,
    answer,
):
    registry, _provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())

    remembered = await orchestrator.handle(statement)
    recalled = await orchestrator.handle(question)

    assert remembered.intent == "memory_remember"
    assert recalled.intent == "memory_recall"
    assert recalled.response == answer
    assert recalled.executor == "oblivia-memory"
    assert recalled.metadata["selected_route"] == "memory_provider"
    assert recalled.metadata["memory_action"] == "recall"
    assert recalled.metadata["a2a_used"] is True
    assert recalled.metadata["llm_used"] is False
    assert recalled.metadata["memory_facts"]


@pytest.mark.asyncio
async def test_lives_at_temporal_transition_history_and_idempotence(
    tmp_path,
    monkeypatch,
):
    registry, provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())

    await orchestrator.handle("J'habite à Saron-sur-Aube.")
    initial = provider._manager.sqlite.list_lives_at()
    assert len(initial) == 1
    assert initial[0].object == "Saron-sur-Aube"
    assert initial[0].is_current is True
    assert initial[0].valid_to is None

    await orchestrator.handle("J'habite maintenant à Troyes.")
    timeline = provider._manager.sqlite.list_lives_at()
    assert len(timeline) == 2
    assert timeline[0].object == "Saron-sur-Aube"
    assert timeline[0].is_current is False
    assert timeline[0].valid_to is not None
    assert timeline[1].object == "Troyes"
    assert timeline[1].is_current is True
    assert timeline[1].valid_to is None
    assert timeline[0].valid_to == timeline[1].valid_from

    expected = {
        "Où est-ce que j'habite ?": "Tu habites à Troyes.",
        "Où est-ce que j'habitais avant ?": (
            "Avant, tu habitais à Saron-sur-Aube."
        ),
        "Où habitais-je avant ?": "Avant, tu habitais à Saron-sur-Aube.",
        "Où ai-je vécu ?": (
            "Tu as vécu à Saron-sur-Aube, puis à Troyes."
        ),
        "Dans quelles villes ai-je vécu ?": (
            "Tu as vécu à Saron-sur-Aube, puis à Troyes."
        ),
    }
    for question, answer in expected.items():
        recalled = await orchestrator.handle(question)
        assert recalled.intent == "memory_recall"
        assert recalled.response == answer
        assert recalled.executor == "oblivia-memory"
        assert recalled.metadata["memory_action"] == "recall"
        assert recalled.metadata["a2a_used"] is True
        assert recalled.metadata["llm_used"] is False

    before_repeat = [
        fact.model_dump(mode="json")
        for fact in provider._manager.sqlite.list_lives_at()
    ]
    fact_count = len(provider._manager.sqlite.list_facts())
    repeated = await orchestrator.handle("J'habite à Troyes.")
    after_repeat = [
        fact.model_dump(mode="json")
        for fact in provider._manager.sqlite.list_lives_at()
    ]

    assert repeated.intent == "memory_remember"
    assert after_repeat == before_repeat
    # L'idempotence porte sur les FAITS, pas sur les messages bruts :
    # save_record insere une ligne par message (id neuf a chaque fois) et
    # la memoire garde deliberement chaque message recu. Repeter une phrase
    # ne doit donc rien changer au savoir, mais ajoute bien une ligne au
    # journal des messages.
    assert len(provider._manager.sqlite.list_facts()) == fact_count


@pytest.mark.asyncio
async def test_lives_at_history_is_unique_by_normalized_value_in_rendering(
    tmp_path,
    monkeypatch,
):
    registry, provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())

    for statement in (
        "J'habite à Saron-sur-Aube.",
        "J'habite à Troyes.",
        "J'habite à Saron-sur-Aube.",
        "J'habite à Troyes.",
        "J'habite à Saron-sur-Aube.",
    ):
        await orchestrator.handle(statement)

    recalled = await orchestrator.handle("Où ai-je vécu ?")
    audit = provider._manager.sqlite.list_lives_at()

    assert recalled.response == (
        "Tu as vécu à Saron-sur-Aube, puis à Troyes."
    )
    assert recalled.metadata["llm_used"] is False
    assert len(audit) == 5
    assert [fact.object for fact in audit] == [
        "Saron-sur-Aube",
        "Troyes",
        "Saron-sur-Aube",
        "Troyes",
        "Saron-sur-Aube",
    ]


@pytest.mark.asyncio
async def test_nonconsecutive_duplicate_is_also_hidden_only_in_rendering(
    tmp_path,
    monkeypatch,
):
    registry, _provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())
    for statement in (
        "J'habite à Saron-sur-Aube.",
        "J'habite à Troyes.",
        "J'habite à Saron-sur-Aube.",
    ):
        await orchestrator.handle(statement)

    recalled = await orchestrator.handle("Où ai-je vécu ?")

    assert recalled.response == (
        "Tu as vécu à Saron-sur-Aube, puis à Troyes."
    )


@pytest.mark.asyncio
async def test_previous_lives_at_without_history_has_clean_non_llm_answer(
    tmp_path,
    monkeypatch,
):
    registry, _provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())
    await orchestrator.handle("J'habite à Troyes.")

    recalled = await orchestrator.handle(
        "Où est-ce que j'habitais avant ?"
    )

    assert recalled.response == (
        "Je ne connais pas de lieu où tu habitais avant."
    )
    assert recalled.intent == "memory_recall"
    assert recalled.executor == "oblivia-memory"
    assert recalled.metadata["a2a_used"] is True
    assert recalled.metadata["llm_used"] is False


@pytest.mark.asyncio
async def test_add_historical_residence_preserves_current_and_is_idempotent(
    tmp_path,
    monkeypatch,
):
    registry, provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())
    await orchestrator.handle("J'habite à Troyes.")

    added = await orchestrator.handle("J’ai habité à Laz il y a 4 ans.")
    timeline = provider._manager.sqlite.list_lives_at()

    assert added.response == "C’est noté : tu as habité à Laz."
    assert len(timeline) == 2
    laz = next(fact for fact in timeline if fact.object == "Laz")
    troyes = next(fact for fact in timeline if fact.object == "Troyes")
    assert laz.is_current is False
    assert laz.retracted is False
    assert laz.metadata["date_approximate"] is True
    assert laz.metadata["years_ago"] == 4
    assert troyes.is_current is True

    current = await orchestrator.handle("Où est-ce que j'habite ?")
    history = await orchestrator.handle("Où ai-je vécu ?")
    assert current.response == "Tu habites à Troyes."
    assert history.response == "Tu as vécu à Laz, puis à Troyes."

    before = [fact.model_dump() for fact in timeline]
    fact_count = len(provider._manager.sqlite.list_facts())
    await orchestrator.handle("J’ai habité à Laz il y a 4 ans.")
    after = [
        fact.model_dump()
        for fact in provider._manager.sqlite.list_lives_at()
    ]
    assert after == before
    # L'idempotence porte sur les FAITS, pas sur les messages bruts :
    # save_record insere une ligne par message (id neuf a chaque fois) et
    # la memoire garde deliberement chaque message recu. Repeter une phrase
    # ne doit donc rien changer au savoir, mais ajoute bien une ligne au
    # journal des messages.
    assert len(provider._manager.sqlite.list_facts()) == fact_count


@pytest.mark.asyncio
async def test_retract_current_residence_keeps_audit_and_is_idempotent(
    tmp_path,
    monkeypatch,
):
    registry, provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())
    await orchestrator.handle("J'habite à Troyes.")

    retracted = await orchestrator.handle(
        "Je n’ai jamais habité à Troyes."
    )
    audit = provider._manager.sqlite.list_lives_at()

    assert retracted.response == (
        "C’est corrigé : Troyes est retiré de ton historique de résidence."
    )
    assert len(audit) == 1
    assert audit[0].object == "Troyes"
    assert audit[0].is_current is False
    assert audit[0].retracted is True
    assert audit[0].retracted_at is not None
    assert audit[0].retraction_reason == "user_denial"

    current = await orchestrator.handle("Où est-ce que j'habite ?")
    history = await orchestrator.handle("Où ai-je vécu ?")
    assert current.response == (
        "Je ne connais pas ton lieu de résidence actuel."
    )
    assert history.response == "Je ne connais aucun lieu où tu as vécu."
    assert current.metadata["llm_used"] is False
    assert history.metadata["llm_used"] is False

    before = [fact.model_dump() for fact in audit]
    fact_count = len(provider._manager.sqlite.list_facts())
    await orchestrator.handle("Je n’ai jamais habité à Troyes.")
    after = [
        fact.model_dump()
        for fact in provider._manager.sqlite.list_lives_at()
    ]
    assert after == before
    # L'idempotence porte sur les FAITS, pas sur les messages bruts :
    # save_record insere une ligne par message (id neuf a chaque fois) et
    # la memoire garde deliberement chaque message recu. Repeter une phrase
    # ne doit donc rien changer au savoir, mais ajoute bien une ligne au
    # journal des messages.
    assert len(provider._manager.sqlite.list_facts()) == fact_count


@pytest.mark.asyncio
async def test_retract_historical_residence_excludes_only_that_place(
    tmp_path,
    monkeypatch,
):
    registry, provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())
    await orchestrator.handle("J'habite à Saron-sur-Aube.")
    await orchestrator.handle("J'habite maintenant à Troyes.")

    await orchestrator.handle(
        "Je n’ai jamais habité à Saron-sur-Aube."
    )

    audit = provider._manager.sqlite.list_lives_at()
    saron = next(
        fact for fact in audit if fact.object == "Saron-sur-Aube"
    )
    troyes = next(fact for fact in audit if fact.object == "Troyes")
    assert saron.retracted is True
    assert saron.is_current is False
    assert troyes.retracted is False
    assert troyes.is_current is True

    current = await orchestrator.handle("Où est-ce que j'habite ?")
    history = await orchestrator.handle("Où ai-je vécu ?")
    previous = await orchestrator.handle(
        "Où est-ce que j'habitais avant ?"
    )
    assert current.response == "Tu habites à Troyes."
    assert history.response == "Tu as vécu à Troyes."
    assert previous.response == (
        "Je ne connais pas de lieu où tu habitais avant."
    )


@pytest.mark.asyncio
async def test_children_collection_end_to_end_remember_then_recall(
    tmp_path,
    monkeypatch,
):
    registry, provider = memory_stack(tmp_path)
    monkeypatch.setattr(
        "core.pipeline.orchestrator.provider_registry",
        registry,
    )
    orchestrator = CoreOrchestrator(agent_router=ForbiddenAgentRouter())

    remembered = await orchestrator.handle(
        "J'ai trois enfants : Lounna, Ninna et Matthyas."
    )

    assert remembered.intent == "memory_remember"
    assert remembered.executor == "oblivia-memory"
    assert remembered.metadata["a2a_used"] is True
    facts = provider._manager.sqlite.list_facts()
    assert {
        (fact.subject, fact.predicate, fact.object)
        for fact in facts
    } == {
        ("user", "has_child", "Lounna"),
        ("user", "has_child", "Ninna"),
        ("user", "has_child", "Matthyas"),
        ("user", "children_count", "3"),
        ("Lounna", "relation_to_user", "child"),
        ("Ninna", "relation_to_user", "child"),
        ("Matthyas", "relation_to_user", "child"),
    }

    expected = {
        "Combien ai-je d'enfants ?": "Tu as trois enfants.",
        "Comment s'appellent mes enfants ?": (
            "Tes enfants s'appellent Lounna, Ninna et Matthyas."
        ),
        "Qui sont mes enfants ?": (
            "Tes enfants sont Lounna, Ninna et Matthyas."
        ),
        "Qui est Lounna ?": "Lounna est l'un de tes enfants.",
        "Qui est Ninna ?": "Ninna est l'un de tes enfants.",
        "Qui est Matthyas ?": "Matthyas est l'un de tes enfants.",
    }
    for question, answer in expected.items():
        recalled = await orchestrator.handle(question)
        assert recalled.intent == "memory_recall"
        assert recalled.response == answer
        assert recalled.executor == "oblivia-memory"
        assert recalled.metadata["selected_route"] == "memory_provider"
        assert recalled.metadata["memory_action"] == "recall"
        assert recalled.metadata["a2a_used"] is True
        assert recalled.metadata["llm_used"] is False


@pytest.mark.asyncio
async def test_existing_knowledge_is_updated_then_forgotten(tmp_path):
    registry, _provider = memory_stack(tmp_path)

    await registry.execute_via_a2a(
        "oblivia-memory",
        ProviderRequest(
            action="remember",
            payload={"content": "Ma femme s'appelle Alice."},
        ),
    )
    await registry.execute_via_a2a(
        "oblivia-memory",
        ProviderRequest(
            action="update",
            payload={"content": "Ma femme s'appelle Claire."},
        ),
    )
    recalled = await registry.execute_via_a2a(
        "oblivia-memory",
        ProviderRequest(
            action="recall",
            payload={"query": "Comment s'appelle ma femme ?"},
        ),
    )
    forgotten = await registry.execute_via_a2a(
        "oblivia-memory",
        ProviderRequest(action="forget", payload={"query": "ma femme"}),
    )
    after_forget = await registry.execute_via_a2a(
        "oblivia-memory",
        ProviderRequest(
            action="recall",
            payload={"query": "Comment s'appelle ma femme ?"},
        ),
    )

    assert recalled.result["answer"] == "Ta femme s'appelle Claire."
    assert len(recalled.result["facts"]) == 1
    assert forgotten.result == {"forgotten": 1}
    assert after_forget.result["answer"] is None


def test_core_has_no_memory_storage_or_business_implementation():
    core_memory = Path(__file__).resolve().parents[1] / "server/core/modules/memory"
    assert not (core_memory / "store.py").exists()
    service = (core_memory / "service.py").read_text(encoding="utf-8")
    assert "sqlite3" not in service
    assert "ObliviaMemoryManager" not in service
    assert "save_memory" not in service


def test_goal_has_no_embedded_memory_backend():
    goal_root = Path(__file__).resolve().parents[1] / "server/goal"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in goal_root.rglob("*.py")
        if "__pycache__" not in path.parts
    )
    assert "ObsidianMemoryAdapter" not in source
    assert "ObliviaMemoryManager" not in source
    assert "core.modules.memory.store" not in source
    assert "/memory/memory.db" not in source
