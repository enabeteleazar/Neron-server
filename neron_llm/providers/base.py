# providers/base.py

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseProvider(ABC):

    @abstractmethod
    async def generate(self, message: str, model: str) -> str:
        ...

    async def aclose(self) -> None:
        pass
