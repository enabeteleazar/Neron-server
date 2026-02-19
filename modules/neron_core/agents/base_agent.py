# agents/base_agent.py
import logging
import time
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
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
