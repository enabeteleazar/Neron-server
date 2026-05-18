class AutonomousScheduler:
    """
    Scheduler autonome minimal pour éviter le crash du Core.
    À remplacer ensuite par le vrai moteur de planification Néron.
    """

    def __init__(self, *args, **kwargs):
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)
        return {"status": "ok", "task": task}

    def list_tasks(self):
        return self.tasks

    def run_pending(self):
        return {"status": "ok", "executed": 0}
