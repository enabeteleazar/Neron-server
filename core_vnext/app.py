# core/app.py
# Néron Core v3 — Bootstrap FastAPI via Control Plane.

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.control_plane.core import NeronCore
from core.gateway.http_gateway import router as http_router

logger = logging.getLogger("neron.app")

# ─────────────────────────────────────────────
# CORE INSTANCE
# ─────────────────────────────────────────────

core = NeronCore()
core.boot()

# ─────────────────────────────────────────────
# FASTAPI LIFECYCLE
# ─────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Démarrage Néron via Control Plane...")

    # Le LifecycleManager itère sur le registry et appelle start()
    # sur tous les services qui l'implémentent (ws_gateway, telegram_gateway…).
    # NE PAS démarrer telegram séparément ici — ça crée un double polling → Conflict.
    if core.lifecycle:
        await core.lifecycle.start_all(core.registry)

    logger.info("Néron démarré")

    yield

    logger.info("Arrêt Néron...")

    if core.lifecycle:
        await core.lifecycle.stop_all(core.registry)

    logger.info("Néron arrêté proprement")


# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────

app = FastAPI(
    title="Néron Core",
    version="3.0.0",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────
# ROUTES HTTP GATEWAY
# ─────────────────────────────────────────────

app.include_router(http_router)

# ─────────────────────────────────────────────
# WEBSOCKET GATEWAY (sous-app FastAPI)
# ─────────────────────────────────────────────

gateway = core.get_gateway()
if gateway:
    ws_app = gateway.http_app()
    if ws_app:
        app.mount("/gateway", ws_app)

# ─────────────────────────────────────────────
# HEALTH ENDPOINT
# ─────────────────────────────────────────────


@app.get("/health")
def health():
    return {
        "status": "ok",
        "gateway_clients": gateway.client_count if gateway else 0,
        "system": core.health.system() if core.health else {},
    }
