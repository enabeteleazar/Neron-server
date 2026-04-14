from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal


class LLMRequest(BaseModel):
    """Contrat d'entrée unique pour toutes les interfaces (HTTP, CLI, interne)."""

    message: str
    task: Optional[str] = Field(default="default", description="Clé de routage vers un modèle")
    mode: Literal["single", "parallel", "race"] = Field(
        default="single",
        description="single=un provider, parallel=tous en parallèle, race=le premier qui répond"
    )
    provider: Optional[str] = Field(default=None, description="Forcer un provider spécifique")
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class LLMResponse(BaseModel):
    """Réponse normalisée pour le mode single."""

    provider: str
    model: str
    response: str


class ParallelLLMResponse(BaseModel):
    """Réponse normalisée pour le mode parallel — tous les résultats."""

    results: Dict[str, str]  # {provider_name: response}


class RaceLLMResponse(BaseModel):
    """Réponse normalisée pour le mode race — le gagnant uniquement."""

    winner: str
    response: str
