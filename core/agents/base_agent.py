# agents/base_agent.py
import logging
import time
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


import sys
import os

class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG':    '[36m',
        'INFO':     '[32m',
        'WARNING':  '[33m',
        'ERROR':    '[31m',
        'CRITICAL': '[35m',
    }
    RESET = '[0m'
    DIM   = '[2m'

    def __init__(self, *args, use_color=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_color = use_color

    def format(self, record):
        msg = record.getMessage()
        ts  = self.formatTime(record, self.datefmt)
        if self.use_color:
            color = self.COLORS.get(record.levelname, self.RESET)
            return (
                f"{self.DIM}{ts}{self.RESET} "
                f"{self.DIM}{record.name}{self.RESET} "
                f"{color}{record.levelname:<8}{self.RESET} "
                f"{color}{msg}{self.RESET}"
            )
        return f"{ts} {record.name} {record.levelname:<8} {msg}"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Couleur seulement si stdout est un vrai terminal
        use_color = os.environ.get("FORCE_COLOR", "") == "1" or (hasattr(sys.stdout, "isatty") and sys.stdout.isatty())
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColorFormatter(datefmt="%H:%M:%S", use_color=use_color))
        logger.addHandler(handler)
        logger.propagate = False
    return logger


@dataclass
class AgentResult:
    success: bool
    content: str
    source: str
    intent: str = "unknown"
    confidence: str = "low"
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    latency_ms: Optional[float] = None


class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"agent.{name}")

    async def on_start(self):
        """Hook de démarrage — override dans les agents si besoin."""
        pass

    @abstractmethod
    async def execute(self, query: str, **kwargs) -> AgentResult:
        pass

    def _success(self, content: str, metadata: Dict[str, Any] = None, latency_ms: float = None) -> AgentResult:
        return AgentResult(
            success=True,
            content=content,
            source=self.name,
            metadata=metadata or {},
            latency_ms=latency_ms
        )

    def _failure(self, error: str, latency_ms: float = None) -> AgentResult:
        self.logger.error(f"[{self.name}] Echec : {error}")
        return AgentResult(
            success=False,
            content="",
            source=self.name,
            error=error,
            latency_ms=latency_ms
        )

    def _timer(self) -> float:
        return time.monotonic()

    def _elapsed_ms(self, start: float) -> float:
        return round((time.monotonic() - start) * 1000, 2)
