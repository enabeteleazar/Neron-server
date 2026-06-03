from core.runtime.tools.tool_manager import tool_manager
from core.runtime.tools.system.journal_tool import JournalTool


def register_default_tools():
    tool_manager.register("journal.read", JournalTool())
    return tool_manager.list_tools()
