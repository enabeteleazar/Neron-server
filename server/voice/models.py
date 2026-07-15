from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SpeechResult:
    audio: bytes
    format: str
    duration: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
