"""Pile mémoire de test : Core -> ObliviaProvider -> service memory reel.

Le Core ne possede plus la memoire : `ObliviaProvider` est un client HTTP
vers le service memory (cf. server/core/providers/memory/oblivia.py). Les
tests le construisaient encore avec un `ObliviaMemoryManager` local, heritage
de l'epoque ou le Core portait la memoire — d'ou `TypeError: takes 1
positional argument but 2 were given`.

Plutot que de simuler les reponses du service, on monte le VRAI service
memory en process sur une base temporaire et on y branche le provider par
un transport ASGI. Les tests gardent leur valeur de bout en bout : ils
traversent reellement le routage HTTP, les routes de memory/app.py et
SQLite, sans reseau ni service demarre.

Effet de bord voulu : une fois le shim installe, plus AUCUN appel du
provider ne peut sortir de la machine. Sans lui, `ObliviaProvider()` vise
son defaut `http://127.0.1.4:8040` — la memoire de PRODUCTION — et un test
qui memorise ecrirait dans les vrais souvenirs.
"""

from __future__ import annotations

from pathlib import Path
import time
from types import SimpleNamespace

import httpx

from core.providers.memory import ObliviaProvider
from core.providers.registry import ProviderRegistry

# Application memory visee par le shim. Les tests s'executent en sequence :
# chaque `memory_stack()` la remplace pour la duree du test courant.
_APP_COURANTE = None


class _ClientASGI(httpx.AsyncClient):
    """Client httpx qui parle a l'app en process au lieu du reseau."""

    def __init__(self, **kwargs):
        kwargs.pop("transport", None)
        if _APP_COURANTE is None:
            raise RuntimeError(
                "aucune application memory de test installee — "
                "appeler memory_stack(tmp_path) avant d'utiliser le provider"
            )
        super().__init__(transport=httpx.ASGITransport(app=_APP_COURANTE), **kwargs)


def _installer_shim() -> None:
    from core.providers.memory import oblivia as oblivia_module

    if isinstance(getattr(oblivia_module, "httpx", None), SimpleNamespace):
        return
    oblivia_module.httpx = SimpleNamespace(AsyncClient=_ClientASGI)


def build_memory_app(tmp_path: Path):
    """Instance du service memory sur une base temporaire.

    `app.state.memory_service` est normalement pose par le lifespan ; on le
    pose a la main, le transport ASGI ne le declenchant pas ici.
    """
    from memory.app import (
        KnowledgeService,
        MemoryService,
        app,
        create_knowledge_provider,
    )

    app.state.memory_service = MemoryService(
        tmp_path / "memory.db", tmp_path / "obsidian"
    )
    app.state.knowledge_service = KnowledgeService(create_knowledge_provider())
    # /health lit app.state.started_at et app.state.registry_client
    # (server/common/service.py) ; le lifespan qui les pose ne tourne pas
    # sous transport ASGI.
    app.state.started_at = time.monotonic()
    app.state.registry_client = None
    return app


def memory_stack(tmp_path: Path) -> tuple[ProviderRegistry, ObliviaProvider]:
    """Registre + provider memoire isoles, prets a l'emploi."""
    global _APP_COURANTE
    _APP_COURANTE = build_memory_app(tmp_path)
    _installer_shim()

    provider = ObliviaProvider()
    # Prise d'inspection pour les tests : ils verifient l'etat STOCKE
    # (list_facts, list_lives_at, status) apres avoir ecrit via HTTP. Le
    # provider distant n'a plus de manager local, on lui rattache celui de
    # l'app en process. Les ecritures et lectures passent bien par le vrai
    # chemin HTTP ; seul le constat final court-circuite le reseau.
    provider._manager = _APP_COURANTE.state.memory_service.oblivia
    registry = ProviderRegistry()
    registry.register(provider)
    return registry, provider
