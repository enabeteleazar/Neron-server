from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from watchdog.routes import router
from watchdog.runtime import WatchdogRuntime


logger = logging.getLogger("watchdog.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = WatchdogRuntime()
    app.state.watchdog_runtime = runtime
    await runtime.start()
    logger.info("Watchdog API listening on port 8050")
    try:
        yield
    finally:
        await runtime.stop()


app = FastAPI(
    title="NéronOS Watchdog",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
