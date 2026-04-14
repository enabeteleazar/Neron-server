from .base import BaseProvider
from neron_llm.core.types import LLMRequest


class ClaudeProvider(BaseProvider):

    def generate(self, request: LLMRequest, model: str) -> str:
        return f"[CLAUDE MOCK] {request.message}"
