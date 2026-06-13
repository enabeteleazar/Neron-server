from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.api.auth import verify_api_key
from core.tools.creator import get_tool_creator
from core.tools.models import ToolNeed
from core.tools.registry import get_tool_registry
from core.tools.runtime import get_tool_runtime


router = APIRouter(prefix="/tools", tags=["tools"])


class ToolExecuteRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class ToolNeedRequest(BaseModel):
    text: str = Field(..., min_length=1)
    domain: str | None = None
    intent: str | None = None
    required_tool_slugs: list[str] = Field(default_factory=list)
    matched_capability: str | None = None

    def to_need(self) -> ToolNeed:
        return get_tool_creator().plan_need(
            self.text,
            domain=self.domain,
            intent=self.intent,
            required_tool_slugs=self.required_tool_slugs,
            matched_capability=self.matched_capability,
        )


@router.get("")
async def list_tools(_: None = Depends(verify_api_key)) -> dict[str, Any]:
    tools = [spec.to_dict() for spec in get_tool_registry().list_tools()]
    return {"count": len(tools), "tools": tools}

@router.get("/diagnostics")
async def tool_diagnostics(_: None = Depends(verify_api_key)) -> dict[str, Any]:
    return get_tool_registry().diagnose_consistency()


@router.post("/plan")
async def plan_tools(
    request: ToolNeedRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    creator = get_tool_creator()
    return creator.plan_from_need(request.to_need())


@router.post("/create-from-need")
async def create_tools_from_need(
    request: ToolNeedRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    creator = get_tool_creator()
    return await creator.create_from_need(request.to_need())


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
