from __future__ import annotations

from memory.oblivia import MemoryRecord, ObliviaMemoryManager


def test_semantic_memory_extracts_graph_facts_and_answers_mission_cases(tmp_path):
    manager = ObliviaMemoryManager(
        sqlite_path=str(tmp_path / "memory.db"),
        obsidian_path=str(tmp_path / "obsidian"),
    )

    for statement in (
        "Je suis ton créateur.",
        "Je travaille chez Constructel.",
        "Mon chien s'appelle Rex.",
        "Ma couleur préférée est le bleu.",
        "J'habite à Saron-sur-Aube.",
    ):
        remembered = manager.remember(MemoryRecord(content=statement))
        assert remembered.metadata["facts"]

    assert "Eléazar Nabet" in manager.recall_knowledge("Qui est ton créateur ?")["answer"]
    assert "Constructel" in manager.recall_knowledge("Où je travaille ?")["answer"]
    assert "Rex" in manager.recall_knowledge("Comment s'appelle mon chien ?")["answer"]
    assert "bleu" in manager.recall_knowledge("Quelle est ma couleur préférée ?")["answer"]
    assert "Saron-sur-Aube" in manager.recall_knowledge("Où j'habite ?")["answer"]

    facts = {
        (fact.subject, fact.predicate, fact.object)
        for fact in manager.sqlite.list_facts(include_retracted=False)
    }
    assert ("assistant", "creator", "Eléazar Nabet") in facts
    assert ("user", "works_at", "Constructel") in facts
    assert ("user.dog", "name", "Rex") in facts
    assert ("user", "favorite_color", "bleu") in facts
    assert ("user", "lives_at", "Saron-sur-Aube") in facts
