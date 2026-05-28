class ToolManager:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, tool):
        self.tools[name] = tool

    def list_tools(self):
        return list(self.tools.keys())

    async def execute(self, name: str, payload: dict | None = None):
        if name not in self.tools:
            raise ValueError(f"Outil inconnu : {name}")

        tool = self.tools[name]
        payload = payload or {}

        if hasattr(tool, "execute"):
            return await tool.execute(payload)

        raise ValueError(f"Outil invalide : {name}")


tool_manager = ToolManager()
