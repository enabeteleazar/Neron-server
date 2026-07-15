from __future__ import annotations

from abc import ABC, abstractmethod

from voice.models import TranscriptionResult


class SttProvider(ABC):
    @abstractmethod
    def load(self) -> object:
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        ...

    @abstractmethod
    def transcribe_file(self, path: str) -> TranscriptionResult:
        ...
