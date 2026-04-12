# neron/agent_router.py
# Agent Router — LLM loop inspiré d'OpenClaw Pi Agent (RPC mode).
# Routage des requêtes entre agents.

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Awaitable

import httpx

from core.modules.sessions import SessionStore, Session
from core.modules.skills import SkillRegistry

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration LLM
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class LLMConfig:
    provider:    str        = "ollama"
    model:       str        = "llama3.2"
    # FIX: base_url externalisée via variable d'env (fallback sur l'IP LAN)
    base_url:    str        = field(
        default_factory=lambda: os.getenv(
            "NERON_OLLAMA_URL", "http://192.168.1.130:8010"
        )
    )
    api_key:     str | None = None
    max_tokens:  int        = 2048
    temperature: float      = 0.7
    timeout:     float      = 120.0
    stream:      bool       = True


# ──────────────────────────────────────────────────────────────────────────────
# Tool dispatch table (extensible)
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class Tool:
    name:         str
    description:  str
    input_schema: dict
    # FIX: typé Callable explicite au lieu de Any
    handler: Callable[..., Awaitable[Any]]


class ToolRegistry:
    """Table de dispatch des outils disponibles pour le LLM."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        logger.debug("Tool enregistré : %s", tool.name)

    def schema_list(self) -> list[dict]:
        """Format attendu par Claude / Ollama tool-use."""
        return [
            {
                "name":         t.name,
                "description":  t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    async def dispatch(self, name: str, inputs: dict) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"Outil inconnu : {name}"}
        try:
            return await tool.handler(**inputs)
        except Exception as e:
            logger.exception("Erreur tool %s", name)
            return {"error": str(e)}

    def setup_defaults(self) -> "ToolRegistry":
        """
        Enregistre les outils de base Neron.
        FIX: renommé default_tools() → setup_defaults() pour plus de clarté.
        """
        self.register(Tool(
            name="get_time",
            description="Retourne l'heure et la date actuelle.",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=_tool_get_time,
        ))
        self.register(Tool(
            name="remember",
            description="Mémorise une information dans la session.",
            input_schema={
                "type": "object",
                "properties": {
                    "key":   {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
            handler=_tool_remember,
        ))
        return self


async def _tool_get_time() -> dict:
    from datetime import datetime
    now = datetime.now()
    return {
        "datetime": now.isoformat(),
        "human":    now.strftime("%A %d %B %Y, %H:%M"),
    }


async def _tool_remember(key: str, value: str) -> dict:
    # NOTE: stub — la persistance réelle doit être connectée à la session.
    # Non implémenté : retourne simplement un accusé de réception.
    return {"stored": False, "key": key, "value": value, "note": "non persisté"}


# ──────────────────────────────────────────────────────────────────────────────
# AgentRouter — cœur du module
# ──────────────────────────────────────────────────────────────────────────────


class AgentRouter:
    """
    Route les messages entrants vers le LLM configuré.
    Gère le streaming, le tool-use, et la persistance en session.
    """

    def __init__(
        self,
        sessions:   SessionStore,
        skills:     SkillRegistry,
        llm_config: LLMConfig    | None = None,
        tools:      ToolRegistry | None = None,
    ) -> None:
        self.sessions = sessions
        self.skills   = skills
        self.llm      = llm_config or LLMConfig()
        self.tools    = tools or ToolRegistry().setup_defaults()
        self._usage:  dict[str, dict] = {}  # session_id → dernière usage

    def last_usage(self, session_id: str) -> dict:
        return self._usage.get(session_id, {})

    # ── API publique ────────────────────────────────────────────────────────

    async def chat_stream(
        self, session_id: str, message: str
    ) -> AsyncIterator[str]:
        """Streame les tokens de la réponse LLM (sans tool-use)."""
        session = self._ensure_session(session_id)
        session.add_user(message)
        # FIX: append_msg() atomique au lieu de save() complet
        self.sessions.append_msg(session, session.history[-1])

        messages     = self._build_messages(session)
        full_response = ""

        async for token in self._llm_stream(messages):
            full_response += token
            yield token

        session.add_assistant(full_response)
        self.sessions.append_msg(session, session.history[-1])

    async def run_stream(
        self,
        session_id: str,
        message:    str,
        thinking:   bool = False,
    ) -> AsyncIterator[dict]:
        """
        Agent loop complet avec tool-use.
        Yield des events Gateway-compatibles.
        FIX: try/finally garantit que save() est toujours appelé,
        même en cas d'exception dans la boucle.
        """
        session = self._ensure_session(session_id)
        session.add_user(message)
        self.sessions.append_msg(session, session.history[-1])

        max_loops  = 8
        loop_count = 0

        try:
            while loop_count < max_loops:
                loop_count += 1
                messages     = self._build_messages(session)
                tools_schema = self.tools.schema_list()

                accumulated = ""
                tool_calls: list[dict] = []
                stop_reason = "end_turn"

                async for chunk in self._llm_stream_full(messages, tools=tools_schema):
                    if chunk["type"] == "token":
                        token        = chunk["text"]
                        accumulated += token
                        yield {"event": "agent.token", "data": {
                            "session_id": session_id,
                            "token":      token,
                        }}
                    elif chunk["type"] == "tool_call":
                        tool_calls.append(chunk["call"])
                        yield {"event": "agent.tool_use", "data": {
                            "session_id": session_id,
                            "tool":       chunk["call"]["name"],
                            "input":      chunk["call"]["input"],
                        }}
                    elif chunk["type"] == "stop":
                        stop_reason              = chunk["reason"]
                        self._usage[session_id]  = chunk.get("usage", {})

                if accumulated:
                    session.add_assistant(accumulated)
                    self.sessions.append_msg(session, session.history[-1])

                if stop_reason != "tool_use" or not tool_calls:
                    break

                # Exécute les tools en parallèle
                results = await asyncio.gather(
                    *[self.tools.dispatch(tc["name"], tc["input"]) for tc in tool_calls]
                )

                for tc, result in zip(tool_calls, results):
                    session.add_tool_result(tc["id"], result)
                    self.sessions.append_msg(session, session.history[-1])
                    yield {"event": "agent.tool_result", "data": {
                        "session_id": session_id,
                        "tool":       tc["name"],
                        "result":     result,
                    }}

        finally:
            # FIX: save() garanti même en cas d'exception (réécriture complète finale)
            self.sessions.save(session)

        yield {"event": "agent.done", "data": {
            "session_id": session_id,
            "usage":      self._usage.get(session_id, {}),
        }}

    # ── Helpers internes ────────────────────────────────────────────────────

    def _ensure_session(self, session_id: str) -> Session:
        session = self.sessions.get(session_id)
        if session is None:
            session = self.sessions.create(session_id)
        return session

    def _build_messages(self, session: Session) -> list[dict]:
        """
        Assemble le contexte complet :
        system prompt + skills injectées + historique.
        FIX: utilise session.messages_for_llm() pour filtrer les clés
        internes (ts) avant envoi au LLM.
        """
        skill_context = self.skills.build_system_injection(session.pending_intent)
        system        = session.system_prompt
        if skill_context:
            system = f"{system}\n\n---\n{skill_context}"

        msgs: list[dict] = [{"role": "system", "content": system}]
        # FIX: messages_for_llm() filtre les timestamps internes
        msgs.extend(session.messages_for_llm())
        return msgs

    # ── LLM calls ───────────────────────────────────────────────────────────

    async def _llm_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream simple — tokens seulement."""
        if self.llm.provider == "ollama":
            async for token in self._ollama_stream(messages):
                yield token
        else:
            async for token in self._claude_stream(messages):
                yield token

    async def _llm_stream_full(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> AsyncIterator[dict]:
        """Stream enrichi avec tool_call et stop events."""
        if self.llm.provider == "ollama":
            async for chunk in self._ollama_stream_full(messages, tools=tools):
                yield chunk
        else:
            async for chunk in self._claude_stream_full(messages, tools=tools):
                yield chunk

    # ── Ollama ──────────────────────────────────────────────────────────────

    async def _ollama_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Streaming via Ollama /api/chat."""
        url     = f"{self.llm.base_url}/api/chat"
        payload = {
            "model":    self.llm.model,
            "messages": messages,
            "stream":   True,
            "options":  {
                "temperature": self.llm.temperature,
                "num_predict": self.llm.max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=self.llm.timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data    = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    async def _ollama_stream_full(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> AsyncIterator[dict]:
        """
        Ollama avec tool-use (format OpenAI tools, Ollama >= 0.3.x).
        FIX: variables mortes tool_calls_buffer et accumulated_content supprimées.
        """
        url     = f"{self.llm.base_url}/api/chat"
        payload: dict = {
            "model":    self.llm.model,
            "messages": messages,
            "stream":   True,
            "options":  {
                "temperature": self.llm.temperature,
                "num_predict": self.llm.max_tokens,
            },
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name":        t["name"],
                        "description": t["description"],
                        "parameters":  t["input_schema"],
                    },
                }
                for t in tools
            ]

        stop_reason = "end_turn"
        usage: dict = {}

        async with httpx.AsyncClient(timeout=self.llm.timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg     = data.get("message", {})
                    content = msg.get("content", "")
                    if content:
                        yield {"type": "token", "text": content}

                    for tc in msg.get("tool_calls", []):
                        fn      = tc.get("function", {})
                        call_id = str(id(tc))
                        yield {"type": "tool_call", "call": {
                            "id":    call_id,
                            "name":  fn.get("name", ""),
                            "input": fn.get("arguments", {}),
                        }}
                        stop_reason = "tool_use"

                    if data.get("done"):
                        usage = {
                            "prompt_tokens":     data.get("prompt_eval_count", 0),
                            "completion_tokens": data.get("eval_count", 0),
                        }
                        break

        yield {"type": "stop", "reason": stop_reason, "usage": usage}

    # ── Claude ──────────────────────────────────────────────────────────────

    def _split_system(
        self, messages: list[dict]
    ) -> tuple[str, list[dict]]:
        """Extrait le message system des messages chat."""
        system    = ""
        chat_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                chat_msgs.append(m)
        return system, chat_msgs

    async def _claude_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Streaming Anthropic via API (SSE text-stream)."""
        system, chat_msgs = self._split_system(messages)
        headers = {
            "x-api-key":         self.llm.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        }
        payload = {
            "model":      self.llm.model,
            "max_tokens": self.llm.max_tokens,
            "system":     system,
            "messages":   chat_msgs,
            "stream":     True,
        }
        async with httpx.AsyncClient(timeout=self.llm.timeout) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        data = json.loads(raw)
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
                    except json.JSONDecodeError:
                        continue

    async def _claude_stream_full(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> AsyncIterator[dict]:
        """Claude avec tool-use streaming (SSE)."""
        system, chat_msgs = self._split_system(messages)
        headers = {
            "x-api-key":         self.llm.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        }
        payload: dict = {
            "model":      self.llm.model,
            "max_tokens": self.llm.max_tokens,
            "system":     system,
            "messages":   chat_msgs,
            "stream":     True,
        }
        if tools:
            payload["tools"] = tools

        current_block: dict = {}
        stop_reason         = "end_turn"
        usage: dict         = {}

        async with httpx.AsyncClient(timeout=self.llm.timeout) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        ev = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    etype = ev.get("type")

                    if etype == "content_block_start":
                        block         = ev.get("content_block", {})
                        current_block = {
                            "type":  block.get("type"),
                            "id":    block.get("id"),
                            "name":  block.get("name"),
                            "input": "",
                        }

                    elif etype == "content_block_delta":
                        delta = ev.get("delta", {})
                        dtype = delta.get("type")
                        if dtype == "text_delta":
                            yield {"type": "token", "text": delta.get("text", "")}
                        elif dtype == "input_json_delta":
                            current_block["input"] = (
                                current_block.get("input", "")
                                + delta.get("partial_json", "")
                            )

                    elif etype == "content_block_stop":
                        if current_block.get("type") == "tool_use":
                            try:
                                parsed_input = json.loads(current_block["input"] or "{}")
                            except json.JSONDecodeError:
                                parsed_input = {}
                            yield {"type": "tool_call", "call": {
                                "id":    current_block.get("id", ""),
                                "name":  current_block.get("name", ""),
                                "input": parsed_input,
                            }}

                    elif etype == "message_delta":
                        stop_reason = ev.get("delta", {}).get("stop_reason", "end_turn")
                        usage       = ev.get("usage", {})

                    elif etype == "message_stop":
                        break

        yield {"type": "stop", "reason": stop_reason, "usage": usage}
