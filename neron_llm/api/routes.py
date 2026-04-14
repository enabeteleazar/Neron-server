"""API routes for neron_llm — fully async."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from neron_llm.core.manager import LLMManager
from neron_llm.core.types import LLMRequest, LLMResponse

logger = logging.getLogger("neron_llm.routes")

router = APIRouter()
manager = LLMManager()


@router.post("/chat", response_model=LLMResponse)
async def chat(request: LLMRequest) -> LLMResponse:
    """Main chat endpoint. Strategy decides the execution mode automatically."""
    logger.info("Chat request: task=%s, mode=%s, provider=%s", request.task, request.mode, request.provider)

    result = await manager.handle(request)

    if result.error:
        logger.warning("Chat error: provider=%s, error=%s", result.provider, result.error)
        # Return 502 if all providers failed, 200 with error field for partial failures
        if result.provider == "none":
            raise HTTPException(status_code=502, detail=result.error)

    return result


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "neron_llm", "version": "1.0.0"}


@router.post("/reload")
async def reload():
    """Force reload the YAML configuration."""
    from neron_llm.config import reload_config
    reload_config()
    # Re-instantiate manager to pick up new config
    global manager
    manager = LLMManager()
    return {"status": "ok", "message": "Configuration reloaded"}