class Executor:

    def __init__(self, agent_router):
        self.router = agent_router

    async def execute(self, plan: str):
        return await self.router.handle(plan)
