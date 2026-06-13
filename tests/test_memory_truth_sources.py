from __future__ import annotations

import sqlite3

import pytest

from core.agents.core import memory_agent
from core.agents.core.memory_agent import MemoryAgent


@pytest.fixture
def isolated_memory_db(monkeypatch, tmp_path):
    db_path = tmp_path / "memory.db"
    monkeypatch.setattr(memory_agent, "DB_PATH", str(db_path))
    memory_agent.init_db()
    return db_path


@pytest.mark.asyncio
async def test_memory_agent_supplies_persisted_context(isolated_memory_db):
    agent = MemoryAgent()
    agent.store("Mon projet favori est Atlas", "Information memorisee.")

    context = await agent.get_context("Atlas")

    assert context is not None
    assert context.startswith("Historique mémoire pertinent")
    assert "Mon projet favori est Atlas" in context


@pytest.mark.asyncio
async def test_memory_agent_async_save_uses_persistent_store(isolated_memory_db):
    agent = MemoryAgent()

    row_id = await agent.save("question", "réponse", {"source": "test"})

    assert row_id > 0
    with sqlite3.connect(isolated_memory_db) as connection:
        row = connection.execute(
            "SELECT input, response FROM memory WHERE id = ?",
            (row_id,),
        ).fetchone()
    assert row == ("question", "réponse")
