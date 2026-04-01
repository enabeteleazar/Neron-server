import uuid
from datetime import datetime

class Task:
    def __init__(self, goal: str):
        self.id = str(uuid.uuid4())
        self.goal = goal
        self.plan = None
        self.result = None
        self.status = "pending"
        self.created_at = datetime.now()
        self.history = []
