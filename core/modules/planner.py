from typing import List, Dict, Any
import asyncio
import logging

logger = logging.getLogger("planner")

class Task:
    def __init__(self, name: str, agent: str, payload: Dict[str, Any]):
        self.name = name
        self.agent = agent
        self.payload = payload
        self.completed = False
        self.result = None

class Planner:
    def __init__(self):
        self.tasks: List[Task] = []

    def add_task(self, task: Task):
        self.tasks.append(task)
        logger.info(f"Task added: {task.name} -> {task.agent}")

    async def execute_task(self, task: Task, agents: Dict[str, Any]):
        agent = agents.get(task.agent)
        if not agent:
            logger.warning(f"Agent {task.agent} introuvable")
            return
        try:
            if hasattr(agent, "execute"):
                task.result = await agent.execute(**task.payload)
                task.completed = True
                logger.info(f"Task {task.name} executed successfully")
        except Exception as e:
            logger.error(f"Task {task.name} failed: {e}")

    async def run(self, agents: Dict[str, Any]):
        for task in self.tasks:
            if not task.completed:
                await self.execute_task(task, agents)
