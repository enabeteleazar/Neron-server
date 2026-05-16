# core/pipeline/routing/agent_router.py

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
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


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("'", " ").replace("’", " ")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def _clean_agent_name(name: str) -> str:
    name = _normalize(name)
    name = name.replace("-", "_").replace(" ", "_")
    name = "".join(c for c in name if c.isalnum() or c == "_")
    if name.endswith("_agent"):
        name = name[:-6]
    return name.strip("_")


def _result_to_text(result: Any) -> str:
    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        return result.get("response", str(result))

    if hasattr(result, "content"):
        return result.content if getattr(result, "success", True) else f"⚠️ {result.error}"

    return str(result)


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
        from core.agent_factory.factory_agent import AgentFactoryAgent
        _agent_factory = AgentFactoryAgent()
    return _agent_factory


def _get_self_model():
    from core.self_model.self_model import get_self_model
    return get_self_model()


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


def _extract_agent_name(query: str, prefixes: list[str]) -> str | None:
    text = _normalize(query)

    for prefix in prefixes:
        prefix_norm = _normalize(prefix)
        if text.startswith(prefix_norm):
            raw_name = text.replace(prefix_norm, "", 1).strip()
            name = _clean_agent_name(raw_name)
            return name or None

    return None


def _extract_agent_name_for_run(query: str) -> str | None:
    return _extract_agent_name(
        query,
        [
            "lance l agent",
            "lance agent",
            "execute l agent",
            "execute agent",
            "exécute l agent",
            "exécute agent",
            "run agent",
        ],
    )


def _extract_agent_name_for_promote(query: str) -> str | None:
    return _extract_agent_name(
        query,
        [
            "valide l agent",
            "valide agent",
            "promeut l agent",
            "promeut agent",
            "active l agent",
            "active agent",
        ],
    )


def _is_promote_request(query: str) -> bool:
    text = _normalize(query)
    return any(
        text.startswith(_normalize(prefix))
        for prefix in (
            "valide l agent",
            "valide agent",
            "promeut l agent",
            "promeut agent",
            "active l agent",
            "active agent",
        )
    )

async def _run_dynamic_agent(query: str) -> str:
    from core.runtime.agents.agent_runtime_manager import get_agent_runtime_manager

    manager = get_agent_runtime_manager()
    agent_name = _extract_agent_name_for_run(query)

    if not agent_name:
        return "Nom d’agent introuvable. Exemple : lance l agent meteo"

    result = await manager.run(agent_name, query)

    if not result["ok"]:
        available = ", ".join(result.get("available", [])) or "aucun"
        return f"Agent introuvable : {agent_name}. Agents disponibles : {available}"

    return result["response"]

    lookup_names = [agent_name, f"{agent_name}_agent"]

    agent = None
    selected_name = None

    for name in lookup_names:
        agent = AGENT_REGISTRY.get(name)
        if agent is not None:
            selected_name = name
            break

    if agent is None:
        available = ", ".join(sorted(AGENT_REGISTRY.keys())) or "aucun"
        return f"Agent introuvable : {agent_name}. Agents disponibles : {available}"

    result = await agent.execute(text=query)
    return _result_to_text(result)


async def _promote_dynamic_agent(query: str) -> str:
    from pathlib import Path

    from core.agent_factory.promoter import promote_agent
    from core.agent_factory.validator import validate_agent

    agent_name = _extract_agent_name_for_promote(query)

    if not agent_name:
        return "Nom d’agent introuvable. Exemple : valide l agent meteo"

    candidates = [
        Path(f"/etc/neron/workspace/agents/{agent_name}_agent.py"),
        Path(f"/etc/neron/workspace/agents/{agent_name}.py"),
    ]

    source = next((path for path in candidates if path.exists()), None)

    if source is None:
        checked = ", ".join(str(path) for path in candidates)
        return f"Agent brouillon introuvable : {agent_name}. Chemins vérifiés : {checked}"

    validation = validate_agent(str(source))

    if not validation["ok"]:
        return f"Validation échouée : {validation['error']}"

    result = promote_agent(str(source))

    if not result["ok"]:
        return f"Promotion échouée : {result['error']}"

    return (
        f"✅ Agent promu : {agent_name}\n"
        f"Source : {result['source']}\n"
        f"Destination : {result['destination']}"
    )


class AgentRouter:
    """
    Dispatch une IntentResult vers l'agent approprié et retourne la réponse.
    """

    def __init__(self, sessions=None, skills=None, llm_config=None, tools=None):
        self.sessions = sessions
        self.skills = skills
        self.llm_config = llm_config
        self.tools = tools

    async def route(self, intent_result, query: str):
        model = _get_self_model()
        intent_name = getattr(
            intent_result,
            "intent",
            str(intent_result),
        )
        intent_confidence = getattr(
            intent_result,
            "confidence",
            None,
        )
        model.set_last_intent(
            intent_name,
            intent_confidence,
        )

        intent = intent_result.intent
        logger.info("[AGENT_ROUTER] dispatching intent=%s", intent)

        if _is_promote_request(query):
            return await _promote_dynamic_agent(query)

        if intent == Intent.SELF_STATUS:
            from core.runtime.agents.agent_runtime_manager import get_agent_runtime_manager

            runtime = get_agent_runtime_manager()
            runtime.reload()

            model.set_agents_available(runtime.list_agents())
            model.set_last_agent("self_model")
            model.set_last_error(None)

            return model.full_status_text() if hasattr(model, 'full_status_text') else model.summary()

        if intent in (Intent.SYSTEM_STATUS, Intent.NETWORK_STATUS):
            model.set_last_agent("system_agent")
            model.set_last_error(None)
            result = await _get_system().run(query)
            return _result_to_text(result)

        if intent == Intent.AGENT_CREATION:
            result = await _get_agent_factory().execute(text=query)
            return _result_to_text(result)

        if intent == Intent.AGENT_LIST:
            return _list_dynamic_agents()

        if intent == Intent.AGENT_RUN:
            return await _run_dynamic_agent(query)

        if intent == Intent.NEWS_QUERY:
            result = await _get_news().run(query)
            return _result_to_text(result)

        if intent == Intent.WEATHER_QUERY:
            result = await _get_weather().run(query)
            return _result_to_text(result)

        if intent == Intent.TODO_ACTION:
            result = await _get_todo().run(query)
            return _result_to_text(result)

        if intent == Intent.WIKI_QUERY:
            result = await _get_wiki().run(query)
            return _result_to_text(result)

        if intent == Intent.TIME_QUERY:
            from core.neron_time.time_provider import get_formatted_time
            return get_formatted_time()

        if intent == Intent.HA_ACTION:
            result = await _get_ha().execute(query)
            return _result_to_text(result)

        if intent == Intent.WEB_SEARCH:
            result = await _get_web().execute(query)
            return _result_to_text(result)

        if intent in (Intent.CODE, Intent.CODE_AUDIT):
            from core.agents.dev.code_audit_agent import CodeAuditAgent
            agent = CodeAuditAgent()
            result = await agent.execute(query)
            return _result_to_text(result)

        if intent == Intent.PERSONALITY_FEEDBACK:
            from core.personality.updater import apply_feedback
            apply_feedback(query)
            return "⚙️ Ajustement de comportement pris en compte."

        memory = _get_memory()
        context = await memory.get_context(query) if hasattr(memory, "get_context") else None
        result = await _get_llm().execute(query, context_data=context)

        if getattr(result, "success", False):
            if hasattr(memory, "save"):
                await memory.save(query, result.content)
            return result.content

        return f"⚠️ Erreur LLM : {getattr(result, 'error', 'erreur inconnue')}"


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
