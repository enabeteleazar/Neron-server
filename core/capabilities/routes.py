from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.api.auth import verify_api_key
from core.capabilities.resolver import CapabilityResolver


router = APIRouter(prefix="/capabilities", tags=["capabilities"])
_resolver: CapabilityResolver | None = None


class CapabilityAnalyzeRequest(BaseModel):
    text: str


def get_capability_resolver() -> CapabilityResolver:
    global _resolver
    if _resolver is None:
        _resolver = CapabilityResolver()
    return _resolver


@router.post("/analyze")
async def analyze_capability(
    payload: CapabilityAnalyzeRequest,
    _: None = Depends(verify_api_key),
):
    analysis = await get_capability_resolver().analyze_async(payload.text)
    return analysis.to_dict()
