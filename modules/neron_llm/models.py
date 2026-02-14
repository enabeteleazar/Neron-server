# modules/neron_llm/models.py

"""
Modèles Pydantic pour le service Néron LLM
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PromptRequest(BaseModel):
    """Requête pour générer une réponse"""
    prompt: str = Field(..., description="Le prompt à envoyer au LLM")
    model: str = Field(default="llama3.2:1b", description="Modèle à utiliser")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=8192)
    system_prompt: Optional[str] = Field(default=None, description="Prompt système")
    context: Optional[List[str]] = Field(default=None, description="Contexte de conversation")


class LLMResponse(BaseModel):
    """Réponse du LLM"""
    response: str = Field(..., description="La réponse générée")
    model: str = Field(..., description="Modèle utilisé")
    tokens_used: Optional[int] = Field(default=None, description="Nombre de tokens utilisés")
    generation_time: Optional[float] = Field(default=None, description="Temps de génération en secondes")


class HealthResponse(BaseModel):
    """Réponse du health check"""
    status: str = Field(..., description="État du service")
    service: str = Field(..., description="Nom du service")
    version: str = Field(..., description="Version du service")
    ollama_connected: bool = Field(..., description="Connexion à Ollama")
    available_models: Optional[List[str]] = Field(default=None)


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée"""
    error: str = Field(..., description="Message d'erreur")
    detail: Optional[str] = Field(default=None, description="Détails de l'erreur")
    status_code: int = Field(..., description="Code HTTP")


class ModelListResponse(BaseModel):
    """Liste des modèles disponibles"""
    models: List[Dict[str, Any]] = Field(..., description="Liste des modèles")


class StreamChunk(BaseModel):
    """Chunk de réponse en streaming"""
    chunk: str = Field(..., description="Fragment de texte")
    done: bool = Field(default=False, description="Indique si c'est le dernier chunk")
