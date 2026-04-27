"""server/core/llm_client — REST client towards neron/llm/."""
from .client import NéronLLMClient
from .types  import LLMGenerateRequest, LLMGenerateResponse, DEGRADED_RESPONSE

__all__ = [
    "NéronLLMClient",
    "LLMGenerateRequest",
    "LLMGenerateResponse",
    "DEGRADED_RESPONSE",
]
