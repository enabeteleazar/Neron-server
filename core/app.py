# core/app.py
# Néron v2.1.0 - Launcher multi-process supervisé

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import time

from dataclasses import dataclass, field
from datetime import datetime, timezone
from multiprocessing import Process
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from serverVNext.core.config import settings

# == Logging ==
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
_log_file = settings.LOGS_DIR / settings.LOG_NERON
_file_handler = logging.FileHandler(_log_file)
_file_handler.setLevel(settings.LOG_LEVEL)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout), _file_handler],
)

logger = logging.getLogger("Néron Launcher")

VERSION = "2.1.0"

# == Configuration ==
MAX_RESTARTS = 5
RSTART_WINDOW = 60
RESTART_DELAY = 5
RESTART_DELAY_MAX = 60
RESTART_BACKOFF_FACTOR = 2
RESTART_BACKOFF_MAX = 300
RESTART_CHECK_INTERVAL = 5

# 🔥 NEW : Pipeline global toggle
PIPELINE_ENABLED = os.getenv("NERON_PIPELINE", "1") == "1"

# ── Utils ──────────────────────────────────────────────────────────────

def utc_now_iso() -> str:
    """Retourne la timestamp UTC au format ISO."""
    return datetime.now(timezone.utc).isoformat()


def _personality_available() -> bool:
    """Vérifie si le module personality est disponible."""
    try:
        import personality  # noqa: F401
        return True
    except ImportError:
        return False


# == Helpers async ==
def _run_async(coro_fn: Callable) -> None:
    """Exécute une coroutine dans sa propre boucle d'événements isolée."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(coro_fn())
    except Exception as e:
        logger.error(f"Error in async function: {e}", exc_info=True)
    finally:
        loop.close()


def _run_agent_class(agent_class) -> None:
    """Instancie et démarre un agent BaseAgent."""
    try:
        agent = agent_class()
        _run_async(agent.start)
    except Exception as e:
        logger.error(f"Error initializing {agent_class.__name__}: {e}", exc_info=True)
        raise


# == Agent Descriptor ==
@dataclass
class AgentDescriptor:
    name: str
    target: Callable
    critical: bool = False
    delay_after: float = 0.0

    process: Process | None = field(default=None, repr=False)
    crash_time: list[float] = field(default_factory=list, repr=False)
    restart_count: int = field(default=0, repr=False)
    restart_delay: float = field(default=RESTART_DELAY, repr=False)
    dead: bool = field(init=False, default=False)


# == Targets ==
def _target_watchdog() -> None:
    from serverVNext.serverVNext.core.agents.watchdog_agent import watchdog_loop, start_watchdog_bot

    async def _run():
        await start_watchdog_bot()
        await watchdog_loop()

    _run_async(_run)


def _target_llm() -> None:
    from serverVNext.serverVNext.core.agents.llm_agent import LLMAgent
    _run_agent_class(LLMAgent)


def _target_web() -> None:
    from serverVNext.serverVNext.core.agents.web_agent import WebAgent
    _run_agent_class(WebAgent)


def _target_telegram() -> None:
    from serverVNext.serverVNext.core.agents.telegram_agent import start_bot
    _run_async(start_bot)


def _target_api() -> None:
    from serverVNext.serverVNext.core.agents.api_agent import APIAgent
    _run_agent_class(APIAgent)


# == Agents Registry ==
AGENTS: list[AgentDescriptor] = [
    AgentDescriptor(name="Watchdog", target=_target_watchdog, critical=True, delay_after=3.0),
    AgentDescriptor(name="API", target=_target_api, critical=True, delay_after=2.0),
    AgentDescriptor(name="LLMAgent", target=_target_llm, critical=True, delay_after=2.0),
    AgentDescriptor(name="WebAgent", target=_target_web, critical=False, delay_after=2.0),
    AgentDescriptor(name="TelegramAgent", target=_target_telegram, critical=False, delay_after=1.0),
]


# == Supervisor ==
class Supervisor:
    def __init__(self, agents: list[AgentDescriptor]) -> None:
        self.agents = agents
        self.running = True

    def _spawn(self, agent: AgentDescriptor) -> None:
        p = Process(target=agent.target, name=agent.name, daemon=True)
        p.start()
        agent.process = p
        agent.restart_delay = RESTART_DELAY

        logger.info(f"Started agent {agent.name} (PID {p.pid})")

    def start_all(self) -> None:
        logger.info("Starting all agents...")
        logger.info(f"Pipeline mode: {'ENABLED' if PIPELINE_ENABLED else 'DISABLED'}")
        logger.info(json.dumps({
            "event": "startup",
            "version": VERSION,
            "pipeline": PIPELINE_ENABLED,
            "agents": [a.name for a in self.agents],
        }))

        for agent in self.agents:
            self._spawn(agent)

            if agent.delay_after > 0:
                logger.info(f"Waiting {agent.delay_after}s for {agent.name}...")
                time.sleep(agent.delay_after)

        logger.info("All agents started. Supervisor running.")

    def _check_agent(self, agent: AgentDescriptor) -> None:
        if agent.dead or agent.process is None:
            return

        if agent.process.is_alive():
            return

        exit_code = agent.process.exitcode
        now = time.monotonic()

        agent.crash_time = [t for t in agent.crash_time if now - t < RSTART_WINDOW]
        agent.crash_time.append(now)

        logger.warning(
            "%-12s crashed (exit=%s) [%d/%d]",
            agent.name,
            exit_code,
            len(agent.crash_time),
            MAX_RESTARTS,
        )

        if len(agent.crash_time) >= MAX_RESTARTS:
            agent.dead = True
            logger.error("%s marked as dead", agent.name)

            if agent.critical:
                logger.critical("Critical agent died → stopping system")
                self.stop_all()
                sys.exit(1)
            return

        delay = min(agent.restart_delay, RESTART_DELAY_MAX)
        logger.info(f"Restarting {agent.name} in {delay}s...")

        time.sleep(delay)

        agent.restart_delay = min(
            agent.restart_delay * RESTART_BACKOFF_FACTOR,
            RESTART_BACKOFF_MAX
        )

        agent.restart_count += 1
        self._spawn(agent)

    def run(self) -> None:
        logger.info(f"Supervisor loop every {RESTART_CHECK_INTERVAL}s")

        while self.running:
            for agent in self.agents:
                self._check_agent(agent)

            if all(a.dead for a in self.agents):
                logger.critical("All agents dead → shutdown")
                break

            time.sleep(RESTART_CHECK_INTERVAL)

    def stop_all(self, timeout: float = 10.0) -> None:
        self.running = False
        logger.info("Stopping all agents...")

        for agent in self.agents:
            p = agent.process
            if p and p.is_alive():
                logger.info(f"Terminating {agent.name}...")
                p.terminate()

        deadline = time.monotonic() + timeout

        for agent in self.agents:
            p = agent.process
            if p and p.is_alive():
                remaining = max(0, deadline - time.monotonic())
                p.join(timeout=remaining)
                if p.is_alive():
                    p.kill()

        logger.info("All agents stopped.")
        logger.info(json.dumps({"event": "shutdown", "version": VERSION}))


# == Signals ==
def _install_signal_handlers(supervisor: Supervisor) -> None:
    def handler(sig, frame):
        sig_name = signal.Signals(sig).name
        logger.info(f"Signal {sig_name} ({sig}) received")
        logger.info(json.dumps({"event": "signal_received", "signal": sig_name}))
        supervisor.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


# == Entry point ==
if __name__ == "__main__":
    try:
        logger.info(json.dumps({
            "event": "launcher_start",
            "version": VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "pid": os.getpid(),
            "timestamp": utc_now_iso(),
        }))
        
        supervisor = Supervisor(AGENTS)
        _install_signal_handlers(supervisor)

        supervisor.start_all()
        supervisor.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(json.dumps({
            "event": "launcher_error",
            "error": str(e),
            "timestamp": utc_now_iso(),
        }), exc_info=True)
        sys.exit(1)
