from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from reminders.infra.security import expected_api_key as _expected_api_key
from reminders.scheduler import run_scheduler_loop
from server.common.paths import service_version
from server.common.service import create_service_app

logger = logging.getLogger("reminders.app")
VERSION = service_version(__file__)
SERVICE_NAME = "reminders"


@asynccontextmanager
async def _setup(app: FastAPI):
    if not _expected_api_key():
        logger.warning(
            "NERON_API_KEY absente : les endpoints /reminders ne sont PAS protégés"
        )

    poll_seconds = float(os.getenv("NERON_REMINDERS_POLL_SECONDS", "30"))
    scheduler_task = asyncio.create_task(run_scheduler_loop(poll_seconds))

    try:
        yield
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("Erreur arrêt scheduler rappels : %s", exc)


app = create_service_app(
    name="reminders",
    title="NéronOS Reminders",
    version=VERSION,
    capabilities=["reminder_management"],
    setup=_setup,
)

from reminders.routes import router as reminders_router

app.include_router(reminders_router)
