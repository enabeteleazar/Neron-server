from __future__ import annotations

from memory.oblivia import ObliviaMemoryManager
from memory.oblivia import MemoryRecord
from memory.oblivia.text_utils import normalize_text


MEMORY_CONTENT = (
    "La mémoire de Néron est centralisée dans /etc/neron/server/memory "
    "avec SQLite et Obsidian."
)


class DummyEmbedder:
    model_name = "dummy"
    model = None

    def embed(self, text: str) -> list[float]:
        return [1.0 if text else 0.0]


def test_normalize_text_ignores_accents_case_and_extra_spaces():
    assert normalize_text("Mémoire de Néron") == "memoire de neron"
    assert normalize_text("MÉMOIRE DE NÉRON") == "memoire de neron"
    assert normalize_text("  mémoire   de   Néron  ") == "memoire de neron"


def test_manager_search_is_accent_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "memory.oblivia.semantic.vector_index.LocalEmbedder",
        DummyEmbedder,
    )

    manager = ObliviaMemoryManager(
        sqlite_path=str(tmp_path / "neron_memory.db"),
        obsidian_path=str(tmp_path / "obsidian"),
    )
    manager.remember(
        MemoryRecord(
            id="accent-insensitive-memory",
            source="memory_manager",
            category="project",
            content=MEMORY_CONTENT,
        )
    )

    variants = [
        "mémoire de Néron",
        "memoire de Neron",
        "MEMOIRE DE NERON",
        "MéMoIrE dE NéRoN",
    ]

    baseline_matches = None

    for query in variants:
        results = manager.search(query)
        matches = [
            (item.backend, item.record.content)
            for item in results
            if MEMORY_CONTENT in item.record.content
        ]

        assert ("sqlite", MEMORY_CONTENT) in matches
        assert matches

        if baseline_matches is None:
            baseline_matches = matches
        else:
            assert matches == baseline_matches
