"""Neron LLM microservice — main entry point.

Usage:
    uvicorn neron_llm.main:app --reload
    uvicorn neron_llm.main:app --host 0.0.0.0 --port 8765
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from neron_llm.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(
    title="Neron LLM",
    description="Microservice LLM intelligent pour l'ecosysteme Neron",
    version="1.0.0",
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "neron_llm.main:app",
        host="0.0.0.0",
        port=8765,
        reload=True,
    )