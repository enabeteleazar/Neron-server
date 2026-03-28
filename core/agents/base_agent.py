# agents/base_agent.py
# Socle commun de tous les agents Neron.

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Logging coloré
# ──────────────────────────────────────────────────────────────────────────────


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG":    "\033[36m",
        "INFO":     "\033[32m",
        "WARNING":  "\033[33m",
        "ERROR":    "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"
    DIM   = "\033[2m"

    def __init__(self, *args: Any, use_color: bool = True, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
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


def get_logger(name: str, level: int | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        use_color = (
            os.environ.get("FORCE_COLOR", "") == "1"
            or (hasattr(sys.stdout, "isatty") and sys.stdout.isatty())
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColorFormatter(datefmt="%H:%M:%S", use_color=use_color))
        logger.addHandler(handler)
        logger.propagate = False

        if level is not None:
            logger.setLevel(level)
        else:
            env_level = os.environ.get("NERON_LOG_LEVEL", "INFO").upper()
            logger.setLevel(getattr(logging, env_level, logging.INFO))

    return logger


# ──────────────────────────────────────────────────────────────────────────────
# AgentResult
# ──────────────────────────────────────────────────────────────────────────────

ConfidenceLevel = Literal["low", "medium", "high"]


@dataclass
class AgentResult:
    success:    bool
    content:    str
    source:     str
    intent:     str                = "unknown"
    confidence: ConfidenceLevel    = "low"
    metadata:   Dict[str, Any]     = field(default_factory=dict)
    error:      Optional[str]      = None
    latency_ms: Optional[float]    = None


# ──────────────────────────────────────────────────────────────────────────────
# BaseAgent
# ──────────────────────────────────────────────────────────────────────────────


class BaseAgent(ABC):
    def __init__(self, name: str) -> None:
        self.name    = name
        self.logger  = get_logger(f"agent.{name}")
        self._running = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def on_start(self) -> None:
        """Hook appelé une fois avant la boucle principale. Override si besoin."""
        pass

    async def on_stop(self) -> None:
        """Hook appelé à l'arrêt. Override si besoin."""
        pass

    async def run(self) -> None:
        """
        Boucle principale de l'agent.
        Par défaut : attend indéfiniment (agent passif/event-driven).
        Override pour les agents avec une boucle active (polling, scheduling…).
        """
        await asyncio.Event().wait()

    async def start(self) -> None:
        """
        Point d'entrée du process agent.
        Appelé par app.py via _run_agent_class().
        Séquence : on_start() → run() → on_stop()
        """
        self._running = True
        self.logger.info("Démarrage de l'agent %s", self.name)
        try:
            await self.on_start()
            await self.run()
        except asyncio.CancelledError:
            self.logger.info("Agent %s annulé", self.name)
        except Exception as e:
            self.logger.exception("Agent %s — exception non gérée : %s", self.name, e)
            raise
        finally:
            self._running = False
            try:
                await self.on_stop()
            except Exception as e:
                self.logger.error("Agent %s — erreur on_stop : %s", self.name, e)
            self.logger.info("Agent %s arrêté", self.name)

    async def reload(self) -> bool:
        """
        Rechargement à chaud de l'agent (appelé par le Watchdog).
        Override dans les agents qui supportent le reload.
        Par défaut : no-op, retourne True.
        """
        self.logger.info("reload() non implémenté pour %s — no-op", self.name)
        return True

    # ── Helpers execute ───────────────────────────────────────────────────────

    @abstractmethod
    async def execute(self, query: str, **kwargs: Any) -> AgentResult:
        """Point d'entrée principal de l'agent pour traiter une requête."""
        ...

    # ── Helpers résultats ─────────────────────────────────────────────────────

    def _success(
        self,
        content:    str,
        metadata:   Dict[str, Any] | None = None,
        latency_ms: float | None          = None,
        confidence: ConfidenceLevel        = "low",
    ) -> AgentResult:
        return AgentResult(
            success    = True,
            content    = content,
            source     = self.name,
            metadata   = metadata or {},
            latency_ms = latency_ms,
            confidence = confidence,
        )

    def _failure(
        self,
        error:      str,
        latency_ms: float | None = None,
    ) -> AgentResult:
        self.logger.error("Echec : %s", error)
        return AgentResult(
            success    = False,
            content    = "",
            source     = self.name,
            error      = error,
            latency_ms = latency_ms,
        )

    def _timer(self) -> float:
        return time.monotonic()

    def _elapsed_ms(self, start: float) -> float:
        return round((time.monotonic() - start) * 1000, 2)


# ──────────────────────────────────────────────────────────────────────────────
# Registre global des agents
# ──────────────────────────────────────────────────────────────────────────────

_agents: Dict[str, BaseAgent] = {}


def register_agent(agent: BaseAgent) -> None:
    """Enregistre un agent globalement, accessible depuis Telegram et Watchdog."""
    _agents[agent.name] = agent
    agent.logger.info("Agent enregistré globalement")


def get_agents() -> Dict[str, BaseAgent]:
    """Retourne tous les agents enregistrés."""
    return _agents
