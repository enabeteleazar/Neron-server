# core/pipeline/planner.py
import asyncio
import time
from typing import List, Dict, Any, Optional
from serverVNext.serverVNext.core.agents.memory_agent import MemoryAgent

# ──────────────────────────────────────────────
# Task
# ──────────────────────────────────────────────
class Task:
    def __init__(self, name: str, agent: str, payload: Optional[Dict[str, Any]] = None):
        self.name = name
        self.agent = agent
        self.payload = payload or {}
        self.state = "pending"  # pending | running | done | failed
        self.result: Any = None
        self.error: Optional[str] = None
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "agent": self.agent,
            "payload": self.payload,
            "state": self.state,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp,
        }

# ──────────────────────────────────────────────
# Planner
# ──────────────────────────────────────────────
class Planner:
    def __init__(self, memory: MemoryAgent):
        self.tasks: List[Task] = []
        self.history: List[Task] = []
        self.memory = memory

    def add_task(self, task: Task):
        """Ajoute une tâche à la file d'attente."""
        self.tasks.append(task)

    async def run_task(self, task: Task, agents: Dict[str, Any]):
        """Exécute une tâche avec l'agent correspondant et sauvegarde en mémoire."""
        task.state = "running"
        try:
            agent_instance = agents.get(f"{task.agent}_agent")
            if not agent_instance:
                raise ValueError(f"Agent '{task.agent}' not found")
            
            # Exécution async de la tâche
            task.result = await agent_instance.execute(task.payload)
            task.state = "done"

        except Exception as e:
            task.state = "failed"
            task.error = str(e)

        finally:
            # Stocke la tâche exécutée dans la mémoire
            self.memory.store_task(task.to_dict())
            self.history.append(task)

    async def run(self, agents: Dict[str, Any]):
        """Exécute toutes les tâches en file et vide la file après."""
        for task in self.tasks:
            await self.run_task(task, agents)
        self.tasks = []

    def get_history(self) -> List[Dict[str, Any]]:
        """Retourne l'historique complet des tâches exécutées."""
        return [t.to_dict() for t in self.history]

    def get_pending(self) -> List[Dict[str, Any]]:
        """Retourne la liste des tâches encore en attente."""
        return [t.to_dict() for t in self.tasks]

    def clear_history(self):
        """Vide l'historique des tâches."""
        self.history = []

    def get_last_task(self) -> Optional[Dict[str, Any]]:
        """Retourne la dernière tâche exécutée."""
        if not self.history:
            return None
        return self.history[-1].to_dict()
