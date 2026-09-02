from __future__ import annotations

import pytest

import asyncio
from pathlib import Path

from core.identity import get_identity
from core.modules.identity import detect_identity_intent
from core.modules.identity import service as identity_service
from core.modules.identity.service import (
    build_identity_response,
    build_identity_response_async,
)

PIPELINE_TOKENS = (
    "Goal",
    "Planner",
    "Agent Creator",
    "Codex",
    "Tests",
    "Validation",
    "Registry",
    "Runtime",
)


def _write_identity(path: Path) -> None:
    path.write_text(
        """# NERON.md

# NÉRON OPERATING CONTEXT

Version: 0.2.0

# 1. Mission

Néron est un système cognitif autonome local orienté :
- orchestration d’agents spécialisés
- mémoire persistante
- supervision runtime
- gouvernance cognitive
- assistance continue
- raisonnement distribué

Néron n’est pas un simple chatbot.

# 1.1 Identité

Néron est un système d’exploitation personnel piloté par l’IA.

Sa fonction principale est de superviser un écosystème d’agents permanents au travers :

- d’un point d’entrée unique (Assistant)
- d’un centre de contrôle (Dashboard)
- d’un moteur cognitif orchestré

Le LLM est un composant interchangeable et ne constitue pas l’identité du système.

Le cœur opérationnel de Néron repose sur le pipeline :

Goal
→ Planner
→ Agent Creator
→ Codex
→ Tests
→ Validation
→ Registry
→ Runtime

La réussite de ce pipeline constitue l’objectif principal de la V1.

# 3. Architecture centrale

Composants principaux :
- SelfModel
- WorldModel
- GoalSystem
- RuntimeGovernor
- CognitiveLoop
- MemorySystem
""",
        encoding="utf-8",
    )


def _sentence_count(text: str) -> int:
    return text.count(".") + text.count("?") + text.count("!")


def _assert_first_person(text: str) -> None:
    lowered = text.lower()
    assert any(token in lowered for token in ("je ", "j'", "j’", "ma ", "mon ", "mes "))


def test_build_identity_response_identity_is_first_person_without_pipeline(
    monkeypatch,
    tmp_path,
):
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path)
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    result = build_identity_response("identity_short")
    response = result["response"]

    assert "Je suis Néron" in response or "Je suis Neron" in response
    assert result["identity_kind"] == "identity_short"
    assert result["source"] == str(identity_path)
    assert result["llm_used"] is False
    assert _sentence_count(response) <= 2
    assert not all(token in response for token in PIPELINE_TOKENS)
    _assert_first_person(response)


def test_build_identity_response_legacy_identity_kind_maps_to_short(monkeypatch, tmp_path):
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path)
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    result = build_identity_response("identity")

    assert result["identity_kind"] == "identity_short"
    assert _sentence_count(result["response"]) <= 2


def test_build_identity_response_async_falls_back_when_llm_fails(
    monkeypatch,
    tmp_path,
):
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path)
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    async def fail_llm(question: str, identity_context: str) -> str | None:
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(identity_service, "_try_llm_reformulation", fail_llm)

    result = asyncio.run(
        build_identity_response_async("identity_short", question="Qui es-tu ?")
    )

    assert result["llm_used"] is False
    assert result["source"] == str(identity_path)
    assert "Je suis Néron" in result["response"]
    assert result["response"].strip()
    assert _sentence_count(result["response"]) <= 2
    assert not all(token in result["response"] for token in PIPELINE_TOKENS)


def test_build_identity_response_async_uses_valid_llm_reformulation(
    monkeypatch,
    tmp_path,
):
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path)
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    async def reformulate(
        question: str,
        identity_context: str,
        kind: str = "identity_short",
    ) -> str | None:
        return (
            "Je suis Néron, ton système d'exploitation personnel piloté par l'IA. "
            "Je supervise des agents permanents et je m'appuie sur une mémoire persistante."
        )

    monkeypatch.setattr(identity_service, "_try_llm_reformulation", reformulate)

    result = asyncio.run(
        build_identity_response_async("identity_short", question="Qui es-tu ?")
    )

    assert result["llm_used"] is True
    assert result["response"].startswith("Je suis Néron")
    assert _sentence_count(result["response"]) <= 2


def test_identity_detector_distinguishes_response_depths():
    assert detect_identity_intent("Qui es-tu ?")["kind"] == "identity_short"
    assert detect_identity_intent("Tu es qui ?")["kind"] == "identity_short"
    assert detect_identity_intent("Quelle est ta mission ?")["kind"] == "mission"
    assert detect_identity_intent("À quoi sers-tu ?")["kind"] == "mission"
    assert detect_identity_intent("Comment fonctionnes-tu ?")["kind"] == "architecture_summary"
    assert detect_identity_intent("Comment tu fonctionnes ?")["kind"] == "architecture_summary"
    assert detect_identity_intent("Explique ton architecture")["kind"] == "architecture_detailed"
    assert detect_identity_intent("Décris ton architecture")["kind"] == "architecture_detailed"
    assert detect_identity_intent("Décris-toi complètement")["kind"] == "identity_full"
    assert detect_identity_intent("Présente-toi en détail")["kind"] == "identity_full"


def test_fallback_mission_is_longer_than_short_but_reasonable(monkeypatch, tmp_path):
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path)
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    short = build_identity_response("identity_short")["response"]
    mission = build_identity_response("mission")["response"]

    assert len(mission) > len(short)
    assert 2 <= _sentence_count(mission) <= 4
    _assert_first_person(mission)


def test_fallback_architecture_summary_mentions_major_components(monkeypatch, tmp_path):
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path)
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    response = build_identity_response("architecture_summary")["response"]

    assert any(component in response for component in ("Core", "Oblivia", "Goal"))
    assert _sentence_count(response) <= 5
    _assert_first_person(response)


def test_fallback_architecture_detailed_is_more_detailed(monkeypatch, tmp_path):
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path)
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    summary = build_identity_response("architecture_summary")["response"]
    detailed = build_identity_response("architecture_detailed")["response"]

    assert len(detailed) > len(summary)
    assert "Core" in detailed
    assert "Runtime" in detailed
    _assert_first_person(detailed)


def test_identity_short_is_not_raw_neron_markdown_copy(monkeypatch, tmp_path):
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path)
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    response = build_identity_response("identity_short")["response"]
    source = identity_path.read_text(encoding="utf-8")

    assert response not in source
    assert "Sa fonction principale est de superviser un écosystème" not in response


@pytest.mark.skip(
    reason=(
        "Phase 2B : mecanisme corrige, FORMAT encore divergent. "
        "CE QUI EST REGLE : core/identity/loader.py honore desormais "
        "NERON_IDENTITY_PATH (il codait son repertoire en dur) et reexpose la "
        "cle 'source'. "
        "CE QUI RESTE : deux formats d identite coexistent. Le loader parse du "
        "cle:valeur (Name:, Rôle:, Mission:) — format de "
        "core/identity/documents/NERON.md. core/modules/identity/service.py et "
        "ce fixture parsent des titres Markdown (# Mission, # Identité) — "
        "format de memory/obsidian/identity/NERON.md. "
        "Choisir le format canonique et fusionner les deux NERON.md est une "
        "decision humaine : voir rapport Phase 2B, section Decisions."
    )
)
def test_identity_loader_still_parses_official_path(monkeypatch, tmp_path):
    """NERON_IDENTITY_PATH est la source de verite du corpus d identite.

    ANCIEN CONTRAT  : l identite tenait dans UN fichier designe par
                      NERON_IDENTITY_PATH.
    NOUVEAU CONTRAT : le corpus compte QUATRE documents (NERON.md,
                      PERSONALITY.md, CONVERSATION.md, CONTEXT.md) ;
                      NERON_IDENTITY_PATH designe le NERON.md canonique et les
                      compagnons vivent a cote. IdentityValidator les exige tous.
    RAISON          : Phase 2B — le loader ignorait totalement la variable
                      (repertoire code en dur) ; il la respecte desormais et
                      reexpose la cle 'source'. La forme du corpus, elle, n a
                      pas ete modifiee : c est une decision ouverte.
    """
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path)
    for companion in ("PERSONALITY.md", "CONVERSATION.md", "CONTEXT.md"):
        (tmp_path / companion).write_text(f"Contenu {companion}", encoding="utf-8")
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    identity = get_identity()

    assert identity["name"] == "Néron"
    assert identity["source"] == str(identity_path)


# ---------------------------------------------------------------------------
# Phase 2B — resolution canonique du corpus d identite.
# NERON_IDENTITY_PATH est la source de verite officielle. Ces tests verrouillent
# le mecanisme corrige : avant, core/identity/loader.py codait son repertoire en
# dur et ignorait totalement la variable.
# ---------------------------------------------------------------------------

def test_identity_dir_defaults_to_core_corpus(monkeypatch):
    from core.identity.loader import DEFAULT_IDENTITY_DIR, identity_dir

    monkeypatch.delenv("NERON_IDENTITY_PATH", raising=False)

    assert identity_dir() == DEFAULT_IDENTITY_DIR
    assert (DEFAULT_IDENTITY_DIR / "NERON.md").exists()


def test_identity_dir_follows_env_pointing_at_a_file(monkeypatch, tmp_path):
    """NERON_IDENTITY_PATH designe le NERON.md ; les compagnons sont a cote."""
    from core.identity.loader import identity_dir, identity_document_path

    monkeypatch.setenv("NERON_IDENTITY_PATH", str(tmp_path / "NERON.md"))

    assert identity_dir() == tmp_path
    assert identity_document_path() == tmp_path / "NERON.md"
    assert identity_document_path("PERSONALITY.md") == tmp_path / "PERSONALITY.md"


def test_identity_dir_accepts_a_directory(monkeypatch, tmp_path):
    from core.identity.loader import identity_dir

    monkeypatch.setenv("NERON_IDENTITY_PATH", str(tmp_path))

    assert identity_dir() == tmp_path


def test_identity_resolution_is_not_cached(monkeypatch, tmp_path):
    """La resolution doit etre dynamique, sinon la variable reste inoperante."""
    from core.identity.loader import identity_dir

    monkeypatch.setenv("NERON_IDENTITY_PATH", str(tmp_path / "a" / "NERON.md"))
    first = identity_dir()
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(tmp_path / "b" / "NERON.md"))

    assert first != identity_dir()


def test_get_identity_exposes_its_source(monkeypatch):
    """La provenance doit etre lisible : c est ce qui rend la source verifiable."""
    monkeypatch.delenv("NERON_IDENTITY_PATH", raising=False)

    identity = get_identity()

    assert identity["source"].endswith("/NERON.md")
    assert Path(identity["source"]).exists()


# ---------------------------------------------------------------------------
# Phase 2C — NERON.md structure = source canonique, documents compagnons
# optionnels. Avant ce correctif, l absence de PERSONALITY.md/CONVERSATION.md/
# CONTEXT.md levait IdentityError (loader) puis IdentityValidationError
# (validator) : Neron n avait alors pas d identite tant que les trois
# documents compagnons n etaient pas ecrits, ce qui contredit la regle posee
# par Phase 2C (NERON.md structure obligatoire, le reste optionnel).
# ---------------------------------------------------------------------------

def _write_structured_neron_md(path: Path) -> None:
    path.write_text(
        "Name: Atlas\n"
        "Version: 1.0\n"
        "Rôle: Systeme cognitif local\n"
        "Mission: Superviser des agents\n",
        encoding="utf-8",
    )


def test_get_identity_succeeds_without_companion_documents(monkeypatch, tmp_path):
    """NERON.md seul suffit : les 3 documents compagnons peuvent etre absents."""
    identity_path = tmp_path / "NERON.md"
    _write_structured_neron_md(identity_path)
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    identity = get_identity()

    assert identity["name"] == "Atlas"
    assert identity["role"] == "Systeme cognitif local"
    assert identity["mission"] == "Superviser des agents"
    assert identity["personality"] == ""
    assert identity["conversation"] == ""
    assert identity["context"] == ""


def test_get_identity_fails_without_the_structured_neron_md(monkeypatch, tmp_path):
    """NERON.md, lui, reste obligatoire : sa seule absence doit encore lever."""
    from core.identity.loader import IdentityError

    monkeypatch.setenv("NERON_IDENTITY_PATH", str(tmp_path / "NERON.md"))

    with pytest.raises(IdentityError):
        get_identity()
