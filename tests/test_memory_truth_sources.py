from __future__ import annotations

import pytest

from agents.builtin.core import memory_agent
from agents.builtin.core.memory_agent import MemoryAgent
from core.providers.memory import ObliviaProvider
from core.providers.registry import ProviderRegistry
from tests._memory_stack import memory_stack


@pytest.fixture
def isolated_memory(monkeypatch, tmp_path):
    registry, provider = memory_stack(tmp_path)
    monkeypatch.setattr(memory_agent, "provider_registry", registry)
    # La fixture rend le manager en process : les tests constatent l'etat
    # stocke apres avoir ecrit via le provider (donc via HTTP).
    return provider._manager


@pytest.mark.asyncio
async def test_memory_agent_supplies_context_via_oblivia(isolated_memory):
    agent = MemoryAgent()
    await agent.save("Mon projet favori est Atlas", "Information mémorisée.")

    context = await agent.get_context("Atlas")

    assert context is not None
    assert context.startswith("Mémoire pertinente")
    assert "Mon projet favori est Atlas" in context


@pytest.mark.asyncio
async def test_memory_agent_async_save_uses_oblivia_source_of_truth(
    isolated_memory,
):
    agent = MemoryAgent()

    record_id = await agent.save("question", "réponse", {"source": "test"})
    recent = isolated_memory.recent(limit=1)

    assert record_id
    # manager.recent() rend des MemoryRecord, pas des resultats de
    # recherche : il n'y a pas de niveau .record.
    assert recent[0].id == record_id
    # MemoryAgent.save construit lui-meme ses metadonnees episodiques
    # (input, response, memory_type) et y ajoute celles de l'appelant : elles
    # sont persistees, pas jetees.
    assert recent[0].metadata["source"] == "test"
    assert recent[0].metadata["memory_type"] == "episodic"
    assert recent[0].metadata["input"] == "question"
    assert "Utilisateur: question" in recent[0].content
