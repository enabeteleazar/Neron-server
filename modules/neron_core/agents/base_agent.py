# modules/neron_core/agents/base_agent.py

"""
Classe abstraite de base pour tous les agents Néron.
Chaque agent reçoit une requête et retourne un AgentResult structuré.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging
import json
import time


# ---------------------------------------------------------------------------
# JSON Logging formatter (Fix #6)
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Formate les logs en JSON pour compatibilité monitoring/audit."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger JSON configuré."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


# ---------------------------------------------------------------------------
# AgentResult standardisé (Fix #5)
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """
    Réponse standardisée retournée par tous les agents.
    Champs alignés avec CoreResponse pour cohérence pipeline.
    """
    success: bool
    content: str                              # Contenu principal
    source: str                               # Nom de l'agent
    intent: str = "unknown"                   # Intent ayant déclenché l'agent
    confidence: str = "low"                   # Confiance du routing
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    latency_ms: Optional[float] = None        # Latence d'exécution (Fix #7 prep)


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """
    Classe de base pour tous les agents Néron.

    Un agent est un module spécialisé qui sait répondre
    à un type précis de requête. Il ne parle jamais
    directement au LLM — c'est le Core qui décide.
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"agent.{name}")

    @abstractmethod
    async def execute(self, query: str, **kwargs) -> AgentResult:
        """
        Exécute la logique de l'agent.

        Args:
            query: La requête de l'utilisateur
            **kwargs: Paramètres optionnels selon l'agent

        Returns:
            AgentResult structuré
        """
        pass

    def _success(self, content: str, metadata: Dict[str, Any] = None,
                 latency_ms: float = None) -> AgentResult:
        return AgentResult(
            success=True,
            content=content,
            source=self.name,
            metadata=metadata or {},
            latency_ms=latency_ms
        )

    def _failure(self, error: str, latency_ms: float = None) -> AgentResult:
        self.logger.error(json.dumps({
            "agent": self.name,
            "event": "failure",
            "error": error
        }))
        return AgentResult(
            success=False,
            content="",
            source=self.name,
            error=error,
            latency_ms=latency_ms
        )

    def _timer(self) -> float:
        """Retourne le timestamp courant pour calcul de latence."""
        return time.monotonic()

    def _elapsed_ms(self, start: float) -> float:
        return round((time.monotonic() - start) * 1000, 2)
