"""Data models for neron_llm — standardized request/response formats."""

from __future__ import annotations

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    """Incoming request to the LLM service."""

    message: str
    task: Optional[str] = Field(
        default=None,
        description="Task type: fast, default, code, chat, etc.",
    )
    mode: Optional[Literal["single", "parallel", "race"]] = Field(
        default=None,
        description="Execution mode override. If unset, strategy decides.",
    )
    provider: Optional[str] = Field(
        default=None,
        description="Provider override: ollama, claude, etc.",
    )
    model: Optional[str] = Field(
        default=None,
        description="Model override. If unset, router decides.",
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional metadata passthrough.",
    )


class LLMResponse(BaseModel):
    """Standardized response format — every endpoint returns this."""

    model: str
    provider: str
    response: str
    error: Optional[str] = None