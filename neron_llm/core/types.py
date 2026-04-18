# neron_llm/core/types.py
# Data models for neron_llm — standardized request/response formats.

from __future__ import annotations
from typing import Dict, Literal, Optional
from pydantic import BaseModel, Field


# ── Internal types (LLMManager / providers) ───────────────────────────────────

class LLMRequest(BaseModel):

    message:  str
    task:     Optional[str]                              = Field(default=None)
    mode:     Optional[Literal["single", "parallel", "race"]] = Field(default=None)
    provider: Optional[str]                              = Field(default=None)
    model:    Optional[str]                              = Field(default=None)
    metadata: Optional[Dict[str, str]]                   = Field(default=None)


class LLMResponse(BaseModel):

    model:    str
    provider: str
    response: str
    error:    Optional[str] = None


# ── Public bus contract ───────────────────────────────────────────────────────

class GenerateRequest(BaseModel):

    task_type:        Literal["code", "reasoning", "chat", "agent"] = Field(default="chat")
    prompt:           str
    context:          Dict[str, str]  = Field(default_factory=dict)
    model_preference: str             = Field(default="auto")
    request_id:       str             = Field(default="")


class GenerateResponse(BaseModel):

    result:     str
    model_used: str
    latency_ms: int
    warning:    Optional[str] = None
