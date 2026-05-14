# core/pipeline/routing/agent_router.py

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.pipeline.intent.intent_router import Intent, IntentResult

logger = logging.getLogger("pipeline.agent_router")

_llm: Optional[object] = None
_memory: Optional[object] = None
_system: Optional[object] = None
_ha: Optional[object] = None
_web: Optional[object] = None
_news: Optional[object] = None
_weather: Optional[object] = None
_todo: Optional[object] = None
_wiki: Optional[object] = None
_agent_factory: Optional[object] = None


def _get_llm():
    global _llm
    if _llm is None:
        from core.agents.core.llm_agent import LLMAgent
        _llm = LLMAgent()
    return _llm


def _get_memory():
    global _memory
    if _memory is None:
        from core.agents.core.memory_agent import MemoryAgent
        _memory = MemoryAgent()
    return _memory


def _get_system():
    global _system
    if _system is None:
        from core.agents.core.system_agent import SystemAgent
        _system = SystemAgent()
    return _system


def _get_ha():
    global _ha
    if _ha is None:
        from core.agents.automation.ha_agent import HAAgent
        _ha = HAAgent()
    return _ha


def _get_web():
    global _web
    if _web is None:
        from core.agents.communication.web_agent import WebAgent
        _web = WebAgent()
    return _web


def _get_news():
    global _news
    if _news is None:
        from core.agents.io.news_agent import NewsAgent
        _news = NewsAgent()
    return _news


def _get_weather():
    global _weather
    if _weather is None:
        from core.agents.io.weather_agent import WeatherAgent
        _weather = WeatherAgent()
    return _weather


def _get_todo():
    global _todo
    if _todo is None:
        from core.agents.core.todo_agent import TodoAgent
        _todo = TodoAgent()
    return _todo


def _get_wiki():
    global _wiki
    if _wiki is None:
        from core.agents.io.wiki_agent import WikiAgent
        _wiki = WikiAgent()
    return _wiki


def _get_agent_factory():
    global _agent_factory
    if _agent_factory is None:
        from core.agents.system.agent_factory_agent import AgentFactoryAgent
        _agent_factory = AgentFactoryAgent()
    return _agent_factory


def _list_dynamic_agents() -> str:
    from core.agent_factory.registry import DynamicAgentRegistry, AGENT_REGISTRY

    registry = DynamicAgentRegistry()
    registry.load_generated_agents()

    agents = sorted(AGENT_REGISTRY.keys())

    if not agents:
        return "Aucun agent dynamique chargé."

    lines = ["Agents dynamiques disponibles :"]
    lines.extend(f"- {name}" for name in agents)

    return "\n".join(lines)


def _extract_agent_name_for_run(query: str) -> str | None:
    text = query.lower().strip()
    text = text.replace("'", " ")
    text = text.replace("’", " ")

    prefixes = [
        "lance l agent",
        "lance agent",
        "execute l agent",
        "execute agent",
        "exécute l agent",
        "exécute agent",
        "run agent",
    ]

    for prefix in prefixes:
        if text.startswith(prefix):
            name = text.replace(prefix, "", 1).strip()
            name = name.replace("-", "_").replace(" ", "_")
            name = "".join(c for c in name if c.isalnum() or c == "_")
            return name or None

    return None


async def _run_dynamic_agent(query: str) -> str:
    from core.agent_factory.registry import DynamicAgentRegistry, AGENT_REGISTRY

    registry = DynamicAgentRegistry()
    registry.load_generated_agents()

    agent_name = _extract_agent_name_for_run(query)

    if not agent_name:
        return "Nom d’agent introuvable. Exemple : lance l agent test_pipeline"

    agent = AGENT_REGISTRY.get(agent_name)

    if agent is None:
        available = ", ".join(sorted(AGENT_REGISTRY.keys())) or "aucun"
        return f"Agent introuvable : {agent_name}. Agents disponibles : {available}"

    result = await agent.execute(text=query)

    if isinstance(result, dict):
        return result.get("response", str(result))

    if hasattr(result, "content"):
        return result.content if getattr(result, "success", True) else f"⚠️ {result.error}"

    return str(result)


class AgentRouter:
    """
    Dispatch une IntentResult vers l'agent approprié et retourne la réponse.
    """

    def __init__(self, sessions=None, skills=None, llm_config=None, tools=None):
        self.sessions = sessions
        self.skills = skills
        self.llm_config = llm_config
        self.tools = tools

    async def route(self, intent_result: IntentResult, query: str) -> str:
        intent = intent_result.intent
        logger.info("[AGENT_ROUTER] dispatching intent=%s", intent)

        if intent in (Intent.SYSTEM_STATUS, Intent.NETWORK_STATUS):
            result = await _get_system().run(query)
            return result.content if result.success else f"⚠️ {result.error}"

        if intent == Intent.AGENT_CREATION:
            result = await _get_agent_factory().execute(text=query)

            if isinstance(result, dict):
                return result.get("response", str(result))

            if hasattr(result, "content"):
                return result.content if getattr(result, "success", True) else f"⚠️ {result.error}"

            return str(result)

        if intent == Intent.AGENT_LIST:
            return _list_dynamic_agents()

        if intent == Intent.AGENT_RUN:
            return await _run_dynamic_agent(query)

        if intent == Intent.NEWS_QUERY:
            return await _get_news().run(query)

        if intent == Intent.WEATHER_QUERY:
            return await _get_weather().run(query)

        if intent == Intent.TODO_ACTION:
            return await _get_todo().run(query)

        if intent == Intent.WIKI_QUERY:
            return await _get_wiki().run(query)

        if intent == Intent.TIME_QUERY:
            from core.neron_time.time_provider import get_formatted_time
            return get_formatted_time()

        if intent == Intent.HA_ACTION:
            result = await _get_ha().execute(query)
            return result.content if result.success else f"⚠️ {result.error}"

        if intent == Intent.WEB_SEARCH:
            result = await _get_web().execute(query)
            return result.content if result.success else f"⚠️ {result.error}"

        if intent in (Intent.CODE, Intent.CODE_AUDIT):
            from core.agents.dev.code_audit_agent import CodeAuditAgent
            agent = CodeAuditAgent()
            result = await agent.execute(query)
            return result.content if result.success else f"⚠️ {result.error}"

        if intent == Intent.PERSONALITY_FEEDBACK:
            from core.personality.updater import apply_feedback
            apply_feedback(query)
            return "⚙️ Ajustement de comportement pris en compte."

        memory = _get_memory()
        context = await memory.get_context(query) if hasattr(memory, "get_context") else None
        result = await _get_llm().execute(query, context_data=context)

        if result.success:
            if hasattr(memory, "save"):
                await memory.save(query, result.content)
            return result.content

        return f"⚠️ Erreur LLM : {result.error}"


from dataclasses import dataclass


@dataclass
class LLMConfig:
    provider: str = "ollama"
    model: str = "mistral"
    base_url: str = "http://localhost:11434"
    max_tokens: int = 2048
    temperature: float = 0.7


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def setup_defaults(self) -> "ToolRegistry":
        return self

    def register(self, name: str, tool: Any) -> "ToolRegistry":
        self._tools[name] = tool
        return self
