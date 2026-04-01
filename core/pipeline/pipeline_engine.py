from .task import Task

class PipelineEngine:

    def __init__(self, planner, executor, verifier, memory_agent):
        self.planner = planner
        self.executor = executor
        self.verifier = verifier
        self.memory = memory_agent

    async def run(self, goal: str):

        task = Task(goal)

        # PLAN
        task.plan = await self.planner.create_plan(goal)

        # EXECUTE
        task.result = await self.executor.execute(task.plan)

        # VERIFY
        valid, feedback = await self.verifier.verify(task.result)

        loop = 0

        while not valid and loop < 3:

            task.history.append({
                "error": feedback
            })

            task.plan = await self.planner.create_plan(
                f"{goal}\nFix error: {feedback}"
            )

            task.result = await self.executor.execute(task.plan)

            valid, feedback = await self.verifier.verify(task.result)

            loop += 1

        # MEMORY
        await self.memory.store(task.goal, task.result)

        return task.result
