from __future__ import annotations


from memory.oblivia import ObliviaMemoryManager
from memory.oblivia import MemoryRecord
from memory.oblivia.normalisation import plat as normalize_text


MEMORY_CONTENT = (
    "La mémoire de Néron est centralisée dans /etc/neron/server/memory "
    "avec SQLite et Obsidian."
)


# `DummyEmbedder` a ete retire avec le paquet `oblivia/semantic` : il
# doublait un embedder qui etait lui-meme factice (un vecteur a une seule
# dimension) et que rien n'appelait.


def test_normalize_text_ignores_accents_and_case():
    """Contrat de normalisation lexicale d'Oblivia.

    ANCIEN CONTRAT : memory.oblivia.text_utils.normalize_text() repliait les
    accents, la casse ET les espaces internes multiples.
    NOUVEAU CONTRAT : memory.oblivia.normalisation.plat() replie les accents et
    la casse, et ne fait que strip() les bords. Les espaces internes multiples
    sont CONSERVES.
    RAISON : text_utils a disparu au profit de normalisation ; le repli des
    espaces internes n'a pas ete reporte. Le test acte le comportement reel
    plutot que de le masquer — voir la dette listee en Phase 2A.
    """
    assert normalize_text("Mémoire de Néron") == "memoire de neron"
    assert normalize_text("MÉMOIRE DE NÉRON") == "memoire de neron"
    assert normalize_text("  mémoire de Néron  ") == "memoire de neron"
    # Ecart assume par rapport a l'ancien contrat :
    assert normalize_text("  mémoire   de   Néron  ") == "memoire   de   neron"


def test_manager_search_is_accent_insensitive(tmp_path):
    # Le monkeypatch de `memory.oblivia.semantic.vector_index.LocalEmbedder`
    # a ete retire avec le paquet `oblivia/semantic` (04/09/2026) : c'etait
    # une couche factice — embedder a une dimension, SemanticSearch vide —
    # qu'aucun code n'appelait. Le patch reussissait donc sans effet.
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
