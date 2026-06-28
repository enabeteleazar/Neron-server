from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agents.runtime.runtime import get_agent_runtime
from core.api.auth import verify_api_key


router = APIRouter(prefix="/agents/runtime", tags=["agent-runtime"])


class AgentRunRequest(BaseModel):
    request: str
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
async def runtime_status(_: None = Depends(verify_api_key)) -> dict[str, Any]:
    return get_agent_runtime().status()


@router.get("/executions")
async def list_executions(
    limit: int = 100,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    executions = get_agent_runtime().store.list_executions(limit=limit)
    return {"count": len(executions), "executions": executions}


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    execution = get_agent_runtime().store.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Agent execution not found")
    return execution


@router.post("/run/{agent_slug}")
async def run_agent(
    agent_slug: str,
    payload: AgentRunRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    result = await get_agent_runtime().run_agent(
        agent_slug,
        payload.request,
        context=payload.context,
        metadata=payload.metadata,
    )
    if not result.ok and str(result.error or "").startswith("agent_not_found:"):
        raise HTTPException(status_code=404, detail=result.error)
    if not result.ok and str(result.error or "").startswith(
        "agent_tool_unavailable:"
    ):
        raise HTTPException(status_code=409, detail=result.error)
    return result.to_dict()
