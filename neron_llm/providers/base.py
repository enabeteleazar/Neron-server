from abc import ABC, abstractmethod
from neron_llm.core.types import LLMRequest


class BaseProvider(ABC):

    @abstractmethod
    def generate(self, request: LLMRequest, model: str) -> str:
        pass
