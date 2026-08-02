"""Squelette commun des services Néron.

Monte d office ce que tout service doit avoir : /health homogene,
/metrics, enregistrement au registry, version. N impose pas le cycle
de vie : le travail propre au service passe par `setup`.

Le Core n utilise pas ce squelette (decision du 01/08).
L adresse d annonce vient de l environnement pose par serve.py
(NERON_SERVICE_HOST / NERON_SERVICE_PORT). RegistryClient la relit
lui-meme via service_from_env : les valeurs ci-dessous ne sont qu un
repli pour les lancements hors systemd (tests, mise au point).
"""
from __future__ import annotations

import logging
import os
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, nullcontext
from typing import Any

from fastapi import FastAPI, Request

from server.common.metrics import mount_metrics
from server.common.registry.client import RegistryClient

logger = logging.getLogger("service")


def _env_port() -> int:
    try:
        return int(os.getenv("NERON_SERVICE_PORT", "").strip())
    except ValueError:
        return 0


def create_service_app(
    *,
    name: str,
    title: str,
    version: str,
    capabilities: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    setup: Callable[[FastAPI], Any] | None = None,
    health: Callable[[Request], Any] | None = None,
    register: bool = True,
    **fastapi_kwargs: Any,
) -> FastAPI:
    """Construit une application FastAPI greee pour Neron.

    `setup` est un gestionnaire de contexte asynchrone recevant l app :
    tout ce qui est propre au service s y construit et s y libere.
    `health` renvoie les details a ajouter a la reponse standard.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.service_name = name
        app.state.version = version
        app.state.started_at = time.monotonic()
        app.state.registry_client = None

        async with (setup(app) if setup is not None else nullcontext()):
            # On ne s annonce qu une fois le service reellement pret.
            if register:
                try:
                    client = RegistryClient(
                        service_name=name,
                        version=version,
                        host=os.getenv("NERON_SERVICE_HOST", "127.0.0.1"),
                        port=_env_port(),
                        capabilities=list(capabilities or []),
                        metadata=dict(metadata or {}),
                    )
                    await client.start()
                    app.state.registry_client = client
                except Exception:
                    # Le registre ne doit jamais empecher l API de servir.
                    logger.exception("%s : enregistrement au registry impossible", name)

            try:
                yield
            finally:
                if app.state.registry_client is not None:
                    try:
                        await app.state.registry_client.stop()
                    except Exception:
                        logger.warning("%s : arret du client registry en erreur", name)

    app = FastAPI(title=title, version=version, lifespan=lifespan, **fastapi_kwargs)
    mount_metrics(app, name)

    @app.get("/health")
    async def _health(request: Request) -> dict[str, Any]:
        state = request.app.state
        payload: dict[str, Any] = {
            "service": name,
            "version": version,
            "status": "healthy",
            "uptime_s": round(time.monotonic() - state.started_at, 1),
            "registered": getattr(state.registry_client, "_registered", False),
        }
        if health is not None:
            extra = health(request)
            if hasattr(extra, "__await__"):
                extra = await extra
            payload.update(extra or {})
        return payload

    return app
