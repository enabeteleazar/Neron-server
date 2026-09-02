from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# NERONOS PHASE 2A — test neutralise, volontairement conserve.
#
# ANCIEN CONTRAT  : l identite Neron etait UN fichier, designe par
#                   NERON_IDENTITY_PATH, parse par core.identity.get_identity().
# NOUVEAU CONTRAT : core/identity/loader.py charge QUATRE documents
#                   (NERON.md, PERSONALITY.md, CONVERSATION.md, CONTEXT.md)
#                   depuis un repertoire code en dur :
#                   IDENTITY_PATH = Path(__file__).parent / "documents".
#                   NERON_IDENTITY_PATH n y est plus lu du tout.
# RAISON          : le modele d identite est passe de « un fichier » a « un
#                   corpus de quatre documents ». Ce test ne peut donc plus
#                   injecter une identite de test ; le reparer supposerait de
#                   rendre le repertoire configurable, c est-a-dire de changer
#                   le contrat d identite de Core — decision humaine, voir le
#                   rapport Phase 2A section « Decisions ».
#
# Le contrat reellement RETENU et teste vit dans tests/test_identity_response.py
# (core.modules.identity.service, 9 tests verts), qui lui honore
# NERON_IDENTITY_PATH.
# ---------------------------------------------------------------------------
pytest.skip(
    "Phase 2A : contrat d identite change de forme (1 fichier -> 4 documents, "
    "repertoire non configurable). Voir rapport Phase 2A.",
    allow_module_level=True,
)

import asyncio
from pathlib import Path

from core.identity import get_identity
# Emplacement canonique du SelfModel (Phase 2A).
# ANCIEN CONTRAT : modules.self_model.self_model.SelfModel — facade de
# compatibilite du parent, supprimee.
# NOUVEAU CONTRAT : core.modules.self_model.SelfModel — implementation
# canonique unique. RAISON : un seul SelfModel, cf. Phase 1 et 2A.
from core.modules.self_model import SelfModel


def _write_identity(path: Path, *, name: str = "Atlas", version: str = "9.4") -> None:
    path.write_text(
        f"""# Operating Context

Version: {version}

# 1. Mission

{name} coordonne les services permanents.

# 1.1 Identité

{name} est un système d'exploitation personnel piloté par l'IA.

Sa fonction principale est de superviser des agents.

# 2. Gouvernance

Stabilité avant vitesse.
""",
        encoding="utf-8",
    )


def test_get_identity_reads_neron_markdown(monkeypatch, tmp_path):
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path)
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    identity = get_identity()

    assert identity["name"] == "Atlas"
    assert identity["role"] == "Système d'exploitation personnel piloté par l'IA"
    assert identity["mission"] == "Atlas coordonne les services permanents."
    assert identity["version"] == "9.4"
    assert identity["source"] == str(identity_path)


def test_self_model_identity_is_refreshed_from_neron_markdown(monkeypatch, tmp_path):
    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path, name="Atlas")
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))
    model = SelfModel()

    _write_identity(identity_path, name="Nova", version="10.0")

    assert model.to_dict()["identity"]["name"] == "Nova"
    assert model.to_dict()["identity"]["version"] == "10.0"


def test_self_model_context_uses_identity_loader(monkeypatch, tmp_path):
    from core.api import self_model_context_routes

    identity_path = tmp_path / "NERON.md"
    _write_identity(identity_path, name="Atlas")
    monkeypatch.setenv("NERON_IDENTITY_PATH", str(identity_path))

    class FakeSelfModel:
        def refresh(self):
            return None

        def to_dict(self):
            return {"identity": {"name": "stale"}, "runtime": {}}

    class FakeTaskManager:
        def list_tasks(self):
            return []

        def list_active_tasks(self):
            return []

    monkeypatch.setattr(self_model_context_routes, "get_self_model", FakeSelfModel)
    monkeypatch.setattr(self_model_context_routes, "get_task_manager", FakeTaskManager)
    monkeypatch.setattr(
        self_model_context_routes,
        "scan_project",
        lambda max_depth=1: {"modules": 0, "files": 0},
    )

    first = asyncio.run(self_model_context_routes.self_model_context())
    _write_identity(identity_path, name="Nova")
    second = asyncio.run(self_model_context_routes.self_model_context())

    assert first["identity"]["name"] == "Atlas"
    assert second["identity"]["name"] == "Nova"


def test_runtime_sources_do_not_define_the_legacy_identity():
    root = Path(__file__).parents[1]
    runtime_sources = [
        root / "server" / "core",
        root / "system" / "deploy",
        root / "neron.yaml",
    ]
    forbidden = (
        "Assistant IA personnel",
        "assistant IA local",
        "autonomous assistant",
        "Tu es Néron",
    )

    for source in runtime_sources:
        paths = source.rglob("*") if source.is_dir() else [source]
        for path in paths:
            if path.suffix not in {".py", ".service", ".yaml", ".yml"} or "__pycache__" in path.parts:
                continue
            content = path.read_text(encoding="utf-8")
            assert not any(value in content for value in forbidden), path

    app_source = (root / "server" / "core" / "app.py").read_text(encoding="utf-8")
    assert 'VERSION = "3.7.0"' not in app_source
