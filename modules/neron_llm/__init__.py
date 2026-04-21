# modules/neron_llm/__init__.py

"""
Module Néron LLM
Wrapper HTTP pour Ollama
"""

__version__ = "1.0.0"
__author__ = "Néron AI Team"

from .ollama_client import OllamaClient
from .models import (
    PromptRequest,
    LLMResponse,
    HealthResponse,
    ErrorResponse,
    ModelListResponse
)
from .config import settings

__all__ = [
    "OllamaClient",
    "PromptRequest",
    "LLMResponse",
    "HealthResponse",
    "ErrorResponse",
    "ModelListResponse",
    "settings"
]
