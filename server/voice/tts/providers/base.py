from __future__ import annotations

from abc import ABC, abstractmethod

from voice.models import SpeechResult


class TtsProvider(ABC):
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def synthesize(self, text: str, fmt: str = "mp3") -> SpeechResult:
        ...
