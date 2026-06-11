from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.api.auth import verify_api_key
from core.tools.registry import get_tool_registry
from core.tools.runtime import get_tool_runtime


router = APIRouter(prefix="/tools", tags=["tools"])


class ToolExecuteRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def list_tools(_: None = Depends(verify_api_key)) -> dict[str, Any]:
    tools = [spec.to_dict() for spec in get_tool_registry().list_tools()]
    return {"count": len(tools), "tools": tools}


@router.get("/{slug}")
async def get_tool(slug: str, _: None = Depends(verify_api_key)) -> dict[str, Any]:
    spec = get_tool_registry().get_tool(slug)
    if spec is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return spec.to_dict()


@router.post("/{slug}/execute")
async def execute_tool(
    slug: str,
    request: ToolExecuteRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    result = await get_tool_runtime().execute_tool(slug, request.payload)
    if not result.ok and result.error == "tool_not_found":
        raise HTTPException(status_code=404, detail="Tool not found")
    if not result.ok and result.error == "unsafe_tool_rejected":
        raise HTTPException(status_code=403, detail="Unsafe tool execution rejected")
    return result.to_dict()
