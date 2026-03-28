# server/run.py
# Néron v2 - Launcher multi-process supervisé

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time

from dataclasses import dataclass, field
from multiprocessing import Process
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ==  Logging  ==
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Néron Launcher")

# ==  Configuration  ===
MAX_RESTARTS = 5                    # Nombre maximum de redémarrages pour un agent
RSTART_WINDOW = 60                  # Fenêtre de temps pour compter les redémarrages (en secondes)
RESTART_DELAY = 5                   # Délai avant de tenter un redémarrage (en secondes)   
RESTART_DELAY_MAX = 60              # Délai maximum entre les redémarrages (en secondes)
RESTART_BACKOFF_FACTOR = 2          # Facteur de backoff pour les délais de redémarrage
RESTART_BACKOFF_MAX = 300           # Délai maximum de backoff (en secondes)   
RESTART_CHECK_INTERVAL = 5          # Intervalle de vérification des processus (en secondes)


# ==  Helpers async  ==
def _run_async(coro_fn: Callable) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # Ignore SIGINT dans les processus enfants pour éviter les interruptions non gérées
    signal.signal(signal.SIGTERM, signal.SIG_IGN) # Ignore SIGTERM dans les processus enfants pour permettre au launcher de gérer proprement l'arrêt
    """Lance une fonction async dans un event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro_fn())
    except Exception as e:
        logger.error(f"Error in async function: {e}")
    finally:
        loop.close()

def _run_agent_class(agent_class) -> None:
    """Lance une classe d'agent qui a une méthode start"""
    agent = agent_class()
    _run_async(agent.start)

# ==  Descripteur d'Agents  ==
@dataclass
class AgentDescriptor:
    name:           str
    target:         Callable
    critical:       bool = False    # si True, le launcher tentera de redémarrer l'agent en cas de crash
    delay_after:    float = 0.0     # délai à attendre après le démarrage de l'agent avant de vérifier son état (en secondes)
    
    # Etat runtime
    process:        Process | None  = field(default=None, repr=False)
    crash_time:     list[float]     = field(default_factory=list, repr=False)  # timestamps des crashs pour le calcul du taux de redémarrage
    restart_count: int              = field(default=0, repr=False)  # nombre de redémarrages effectués
    restart_delay: float            = field(default=RESTART_DELAY, repr=False)  # délai actuel avant le prochain redémarrage (en secondes)  
    dead: bool = field(init=False, default=False)  # indique si l'agent est considéré comme mort (trop de redémarrages)

# ==  Entrypoints process  ==
def _target_watchdog() -> None:
    from core.agents.watchdog_agent import watchdog_loop, start_watchdog_bot
    async def _run():
        await start_watchdog_bot()
        await watchdog_loop()
    _run_async(_run)

def _target_llm() -> None:
    from core.agents.llm_agent import LLMAgent
    _run_agent_class(LLMAgent)

def _target_web() -> None:
    from core.agents.web_agent import WebAgent
    _run_agent_class(WebAgent)

def _target_telegram() -> None:
    from core.agents.telegram_agent import start_bot
    _run_async(start_bot)

def _target_api() -> None:
    from core.agents.api_agent import APIAgent
    _run_agent_class(APIAgent)

# ==  Registre des Agents  ==
""" l'ordre définit la sequence de démarrage et de supervision
    delay_after permet de laisser le temps à l'agent de démarrer avant de vérifier son état """

AGENTS: list[AgentDescriptor] = [
    AgentDescriptor(name="Watchdog", target=_target_watchdog, critical=True, delay_after=3.0),
    AgentDescriptor(name="API", target=_target_api, critical=True, delay_after=2.0),
    AgentDescriptor(name="LLMAgent", target=_target_llm, critical=True, delay_after=2.0),
    AgentDescriptor(name="WebAgent", target=_target_web, critical=False, delay_after=2.0),
    AgentDescriptor(name="TelegramAgent", target=_target_telegram, critical=False, delay_after=1.0),
]   

# ==  Supervision et redémarrage  ==
class Supervisor:
    """ Supervise les procss agents et gère le redemarrage automatique en cas de crash """

    def __init__(self, agents: list[AgentDescriptor]) -> None:
        self.agents = agents
        self.running = True

# ==  Démarrage  ==
    def _spawn(self, agent: AgentDescriptor) -> None:
        """ crée et démarre un Process pour un agent donné, et met à jour son descripteur """    
        p = Process(target=agent.target, name=agent.name, daemon=True)
        p.start()
        agent.process = p
        agent.restart_delay = RESTART_DELAY  # reset du délai de redémarrage après un lancement réussi
        logger.info(f"Started agent {agent.name} with PID {p.pid}")

    def start_all(self) -> None:
        """ Démarre tous les agents et supervise leur état en continu """
        logger.info("Starting all agents...")
        for agent in self.agents:
            self._spawn(agent)
            if agent.delay_after > 0:
                logger.info(f"Waiting {agent.delay_after} seconds for {agent.name} to initialize...")
                time.sleep(agent.delay_after)   
        logger.info("All agents started. Entering supervision loop.")

    # ==  Supervision loop  ==
    def _check_agents(self, agent: AgentDescriptor) -> None:
        """ verifie l'état d'un agent, et tente de le redémarrer si nécessaire """
        if agent.dead or agent.process is None:
            return

        if agent.process.is_alive():
            return  # OK

        exit_code = agent.process.exitcode
        now       = time.monotonic()

        # purge des crashs trop anciens
        agent.crash_time = [t for t in agent.crash_time if now - t < RSTART_WINDOW]
        agent.crash_time.append(now)

        logger.warning(
            "%-12s terminé (exit=%s) - crash #%d/%d",
            agent.name,
            exit_code,
            len(agent.crash_time),
            MAX_RESTARTS,
        )

        if len(agent.crash_time) >= MAX_RESTARTS:
            agent.dead = True
            logger.error(
                "%-12s a crashé %d fois dans les %d dernières secondes. Marquage comme mort.",
                agent.name, MAX_RESTARTS, RSTART_WINDOW,
            )
            if agent.critical:
                logger.critical("Agent critique %s mort - arrêt du launcher", agent.name)
                self.stop_all()
                sys.exit(1)
            return

        # Backoff exponentiel pour les redémarrages successifs
        delay = min(agent.restart_delay, RESTART_DELAY_MAX)
        logger.info(f"Redémarrage de {agent.name} dans {delay:.1f} secondes...")
        time.sleep(delay)
        agent.restart_delay = min(agent.restart_delay * RESTART_BACKOFF_FACTOR, RESTART_BACKOFF_MAX)  # augmenter le délai pour le prochain redémarrage en cas de crash répétés    
        agent.restart_count += 1

        self._spawn(agent)

    def run(self) -> None:
        """ Boucle de supervision principale """
        logger.info("Supervisor actif - Intervalle de %ds", RESTART_CHECK_INTERVAL)
        while self.running:
            for agent in self.agents:
                self._check_agents(agent)

            all_dead = all(agent.dead for agent in self.agents)
            if all_dead:
                logger.critical("Tous les agents sont morts - arrêt du launcher")
                break

            time.sleep(RESTART_CHECK_INTERVAL)

    def stop_all(self, timeout: float = 10.0) -> None:
        """ Arret de tous les process proprement """
        self.running = False
        logger.info("Stopping all agents...")
        for agent in self.agents:
            p = agent.process
            try:
                if p and p.is_alive():
                    logger.info(f"Terminating {agent.name} (PID {p.pid})...")
                    p.terminate()
            except Exception:
                pass  # Ignore les erreurs lors de la terminaison, on fera un kill si le process ne s'arrête pas


        deadline = time.monotonic() + timeout
        for agent in self.agents:
            p = agent.process
            try:
                if p and p.is_alive():
                    remaining = max(0.0, deadline - time.monotonic())
                    p.join(timeout=remaining)
                    if p.is_alive():
                         p.kill()
            except Exception:
                pass  # Ignore les erreurs lors de la terminaison, on fera un kill si le process ne s'arrête pas
        logger.info("All agents stopped.")

# == ARRET PROPRE  ==
# ==  Signal handling  ==
def _install_signal_handlers(supervisor: Supervisor) -> None:
    def _handler(sig, frame):
        logger.info(f"Received signal {sig} - stopping all agents...")
        supervisor.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _handler)
    signal.signal(signal.SIGTERM, _handler)
 
# ==  POINT D'ENTREE  ==
if __name__ == "__main__":
    supervisor = Supervisor(AGENTS)
    _install_signal_handlers(supervisor)
    supervisor.start_all()
    supervisor.run()        