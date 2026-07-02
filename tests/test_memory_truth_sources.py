from __future__ import annotations

import pytest

from agents.builtin.core import memory_agent
from agents.builtin.core.memory_agent import MemoryAgent
from core.providers.memory import ObliviaProvider
from core.providers.registry import ProviderRegistry
from memory.oblivia import ObliviaMemoryManager


@pytest.fixture
def isolated_memory(monkeypatch, tmp_path):
    manager = ObliviaMemoryManager(
        sqlite_path=str(tmp_path / "memory.db"),
        obsidian_path=str(tmp_path / "obsidian"),
    )
    registry = ProviderRegistry()
    registry.register(ObliviaProvider(manager))
    monkeypatch.setattr(memory_agent, "provider_registry", registry)
    return manager


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
    assert recent[0].record.id == record_id
    assert recent[0].record.metadata == {}
    assert "Utilisateur: question" in recent[0].record.content
