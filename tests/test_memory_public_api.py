from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.modules.memory import build_memory_response_async
from core.providers.memory import ObliviaProvider
from core.providers.models import ProviderRequest
from core.providers.registry import ProviderRegistry
from memory.oblivia import MemoryRecord, ObliviaMemoryManager


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LEGACY_MODULE = "core.modules" + ".oblivia"


def test_oblivia_public_api_does_not_export_internal_adapters():
    import memory.oblivia as oblivia

    assert {
        "ObliviaMemoryManager",
        "MemoryRecord",
        "MemoryQuery",
        "MemorySearchResult",
        "MemoryStatus",
    } <= set(oblivia.__all__)
    assert "SQLiteMemoryAdapter" not in oblivia.__all__
    assert "ObsidianMemoryAdapter" not in oblivia.__all__


def test_no_python_source_imports_legacy_oblivia_module():
    roots = (REPOSITORY_ROOT / "server", REPOSITORY_ROOT / "tests")
    offenders: list[str] = []

    for root in roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                if any(
                    module == LEGACY_MODULE
                    or module.startswith(f"{LEGACY_MODULE}.")
                    for module in modules
                ):
                    offenders.append(str(path.relative_to(REPOSITORY_ROOT)))

    assert offenders == []


@pytest.mark.asyncio
async def test_core_memory_gateway_uses_registry_a2a(monkeypatch, tmp_path):
    registry = ProviderRegistry()
    registry.register(ObliviaProvider(ObliviaMemoryManager(
        sqlite_path=str(tmp_path / "memory.db"),
        obsidian_path=str(tmp_path / "obsidian"),
    )))
    monkeypatch.setattr("core.modules.memory.service.provider_registry", registry)

    remembered = await build_memory_response_async(
        "remember",
        "Retiens que mon projet est Atlas",
    )
    recalled = await build_memory_response_async("recall", "Quel est mon projet ?")

    assert remembered["a2a_used"] is True
    assert recalled["a2a_used"] is True
    assert recalled["agent"] == "oblivia"


@pytest.mark.asyncio
async def test_public_provider_remember_recall_search_status_and_health(tmp_path):
    provider = ObliviaProvider(ObliviaMemoryManager(
        sqlite_path=str(tmp_path / "memory.db"),
        obsidian_path=str(tmp_path / "obsidian"),
    ))

    health = await provider.health()
    remembered = await provider.execute(ProviderRequest(
        action="remember",
        payload={"content": "Oblivia est la mémoire publique.", "category": "project"},
    ))
    recalled = await provider.execute(ProviderRequest(
        action="recall",
        payload={"query": "Oblivia", "limit": 5},
    ))
    searched = await provider.execute(ProviderRequest(
        action="search",
        payload={"query": "mémoire", "limit": 5},
    ))
    status = await provider.execute(ProviderRequest(action="status"))

    assert health.status == "healthy"
    assert remembered.status == "healthy"
    assert recalled.result["results"]
    assert searched.result
    assert status.result["ok"] is True
