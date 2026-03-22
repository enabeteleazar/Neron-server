"""
neron/gateway.py
================
Gateway WebSocket — Plan de contrôle central inspiré d'OpenClaw.
Port par défaut : ws://0.0.0.0:18789

Architecture :
  Clients (NEXUS front, CLI, WebChat)
         │
         ▼
   ┌──────────────┐
   │   Gateway    │  ← ce fichier
   │  WebSocket   │
   └──────┬───────┘
          │
    ┌─────┴──────┐
    │            │
  Agent        Sessions
  Router       Store
    │
  Ollama / Claude (LLM)

Protocole de frames (JSON) :
  { "method": "chat.send",   "id": "uuid", "params": {...} }
  { "method": "agent.run",   "id": "uuid", "params": {...} }
  { "method": "skill.call",  "id": "uuid", "params": {...} }
  { "method": "session.new", "id": "uuid", "params": {...} }
  { "method": "session.list","id": "uuid", "params": {} }
  { "method": "ping",        "id": "uuid", "params": {} }

Réponses :
  { "id": "uuid", "result": {...} }
  { "id": "uuid", "error":  {"code": int, "message": str} }
  { "event": "agent.token", "data": {"token": str, "session_id": str} }
  { "event": "agent.done",  "data": {"session_id": str, "usage": {...}} }
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

from modules.agent_router import AgentRouter
from modules.sessions import SessionStore
from modules.skills import SkillRegistry

logger = logging.getLogger("neron.gateway")

# ──────────────────────────────────────────────────────────────────────────────
# Dataclasses internes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class GatewayConfig:
    host: str = "0.0.0.0"
    port: int = 18789
    token: str | None = None          # auth optionnelle
    max_connections: int = 64
    ping_interval: float = 20.0
    ping_timeout: float = 10.0

@dataclass
class ConnectedClient:
    ws: WebSocketServerProtocol
    client_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    authenticated: bool = False

# ──────────────────────────────────────────────────────────────────────────────
# Gateway principale
# ──────────────────────────────────────────────────────────────────────────────

class NeronGateway:
    """
    Serveur WebSocket mono-port, multi-clients.
    Dispatch les méthodes JSON-RPC vers AgentRouter / SessionStore / SkillRegistry.
    """

    def __init__(
        self,
        config: GatewayConfig | None = None,
        agent_router: AgentRouter | None = None,
        session_store: SessionStore | None = None,
        skill_registry: SkillRegistry | None = None,
    ):
        self.config = config or GatewayConfig()
        self.sessions = session_store or SessionStore()
        self.skills = skill_registry or SkillRegistry()
        self.agent = agent_router or AgentRouter(
            sessions=self.sessions,
            skills=self.skills,
        )
        self._clients: dict[str, ConnectedClient] = {}

    # ── Entrée serveur ──────────────────────────────────────────────────────

    async def start(self) -> None:
        cfg = self.config
        logger.info("Neron Gateway démarrage sur ws://%s:%d", cfg.host, cfg.port)
        async with websockets.serve(
            self._handle_client,
            cfg.host,
            cfg.port,
            ping_interval=cfg.ping_interval,
            ping_timeout=cfg.ping_timeout,
            max_size=10 * 1024 * 1024,  # 10 MB
        ):
            logger.info("Gateway en écoute ✓")
            await asyncio.Future()  # tourne indéfiniment

    # ── Connexion client ────────────────────────────────────────────────────

    async def _handle_client(self, ws: WebSocketServerProtocol) -> None:
        client = ConnectedClient(ws=ws)
        self._clients[client.client_id] = client
        logger.info("[%s] connexion depuis %s", client.client_id, ws.remote_address)

        # Auth immédiate si token configuré
        if self.config.token is None:
            client.authenticated = True
        else:
            await self._send(ws, _event("gateway.auth_required", {}))

        try:
            async for raw in ws:
                await self._dispatch(client, raw)
        except websockets.ConnectionClosedOK:
            pass
        except websockets.ConnectionClosedError as e:
            logger.warning("[%s] connexion fermée : %s", client.client_id, e)
        finally:
            del self._clients[client.client_id]
            logger.info("[%s] déconnexion", client.client_id)

    # ── Dispatch JSON-RPC ───────────────────────────────────────────────────

    async def _dispatch(self, client: ConnectedClient, raw: str | bytes) -> None:
        try:
            frame = json.loads(raw)
        except json.JSONDecodeError:
            await self._send(client.ws, _error(None, -32700, "Parse error"))
            return

        req_id = frame.get("id")
        method = frame.get("method", "")
        params = frame.get("params", {})

        # ── Auth ──
        if method == "gateway.auth":
            token = params.get("token", "")
            if token == self.config.token:
                client.authenticated = True
                await self._send(client.ws, _result(req_id, {"ok": True}))
            else:
                await self._send(client.ws, _error(req_id, 401, "Token invalide"))
            return

        if not client.authenticated:
            await self._send(client.ws, _error(req_id, 401, "Non authentifié"))
            return

        # ── Méthodes publiques ──
        handlers: dict[str, Any] = {
            "ping":         self._ping,
            "chat.send":    self._chat_send,
            "agent.run":    self._agent_run,
            "session.new":  self._session_new,
            "session.list": self._session_list,
            "session.get":  self._session_get,
            "skill.call":   self._skill_call,
            "skill.list":   self._skill_list,
        }

        handler = handlers.get(method)
        if handler is None:
            await self._send(client.ws, _error(req_id, -32601, f"Méthode inconnue : {method}"))
            return

        try:
            result = await handler(client, params)
            if result is not None:
                await self._send(client.ws, _result(req_id, result))
        except Exception as e:
            logger.exception("[%s] erreur handler %s", client.client_id, method)
            await self._send(client.ws, _error(req_id, 500, str(e)))

    # ── Handlers ────────────────────────────────────────────────────────────

    async def _ping(self, client: ConnectedClient, params: dict) -> dict:
        return {"pong": True}

    async def _session_new(self, client: ConnectedClient, params: dict) -> dict:
        session_id = params.get("session_id") or str(uuid.uuid4())
        system = params.get("system", "Tu es Neron, un assistant IA local.")
        session = self.sessions.create(session_id, system_prompt=system)
        return {"session_id": session.id, "created": True}

    async def _session_list(self, client: ConnectedClient, params: dict) -> dict:
        sessions = self.sessions.list_all()
        return {"sessions": [{"id": s.id, "turns": len(s.history)} for s in sessions]}

    async def _session_get(self, client: ConnectedClient, params: dict) -> dict:
        session_id = params.get("session_id")
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session inconnue : {session_id}")
        return {
            "session_id": session.id,
            "history": session.history,
            "system": session.system_prompt,
        }

    async def _chat_send(self, client: ConnectedClient, params: dict) -> None:
        """
        Streaming : envoie des events agent.token puis agent.done.
        Pas de return direct — répond via send().
        """
        session_id = params.get("session_id", "default")
        message = params.get("message", "")
        req_id = None  # pas de résultat synchrone

        async for token in self.agent.chat_stream(session_id, message):
            await self._send(client.ws, _event("agent.token", {
                "session_id": session_id,
                "token": token,
            }))

        usage = self.agent.last_usage(session_id)
        await self._send(client.ws, _event("agent.done", {
            "session_id": session_id,
            "usage": usage,
        }))

    async def _agent_run(self, client: ConnectedClient, params: dict) -> None:
        """
        Exécution d'un agent avec tool-use. Streame les tokens + tool events.
        """
        session_id = params.get("session_id", "default")
        message = params.get("message", "")
        thinking = params.get("thinking", False)

        async for event in self.agent.run_stream(session_id, message, thinking=thinking):
            await self._send(client.ws, event)

    async def _skill_list(self, client: ConnectedClient, params: dict) -> dict:
        skills = self.skills.list_all()
        return {"skills": [{"name": s.name, "description": s.description} for s in skills]}

    async def _skill_call(self, client: ConnectedClient, params: dict) -> dict:
        name = params.get("name")
        skill_params = params.get("params", {})
        result = await self.skills.call(name, **skill_params)
        return {"result": result}

    # ── Helpers envoi ───────────────────────────────────────────────────────

    async def _send(self, ws: WebSocketServerProtocol, payload: dict) -> None:
        try:
            await ws.send(json.dumps(payload, ensure_ascii=False))
        except websockets.ConnectionClosed:
            pass

    async def broadcast(self, payload: dict) -> None:
        """Envoie à tous les clients connectés."""
        if not self._clients:
            return
        msg = json.dumps(payload, ensure_ascii=False)
        await asyncio.gather(
            *[c.ws.send(msg) for c in self._clients.values()],
            return_exceptions=True,
        )

# ──────────────────────────────────────────────────────────────────────────────
# Helpers frames
# ──────────────────────────────────────────────────────────────────────────────

def _result(req_id: str | None, data: dict) -> dict:
    return {"id": req_id, "result": data}

def _error(req_id: str | None, code: int, message: str) -> dict:
    return {"id": req_id, "error": {"code": code, "message": message}}

def _event(name: str, data: dict) -> dict:
    return {"event": name, "data": data}

# ──────────────────────────────────────────────────────────────────────────────
# Point d'entrée standalone
# ──────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    import os
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    config = GatewayConfig(
        host=os.getenv("NERON_HOST", "0.0.0.0"),
        port=int(os.getenv("NERON_PORT", "18789")),
        token=os.getenv("NERON_TOKEN"),  # None = pas d'auth
    )
    gw = NeronGateway(config=config)
    await gw.start()

if __name__ == "__main__":
    asyncio.run(main())
