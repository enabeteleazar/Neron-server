class AgentRegistry:
    def __init__(self):
        self.agents = {}

    def register(self, name: str, agent, capabilities: list[str] | None = None):
        self.agents[name] = {
            "agent": agent,
            "capabilities": capabilities or []
        }

    def list_agents(self):
        return {
            name: data["capabilities"]
            for name, data in self.agents.items()
        }

    def get(self, name: str):
        if name not in self.agents:
            raise ValueError(f"Agent inconnu : {name}")
        return self.agents[name]["agent"]


agent_registry = AgentRegistry()
