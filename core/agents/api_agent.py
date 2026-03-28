# core/agents/api_agent.py
# Néron v2 — Agent API FastAPI (remplace l'ancien app.py)

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import unicodedata
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import psutil
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Security, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.security.api_key import APIKeyHeader
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel

from core.agents.base_agent import BaseAgent, AgentResult, get_logger
from core.agents.code_agent import CodeAgent
from core.agents.ha_agent import HAAgent
from core.agents.llm_agent import LLMAgent
from core.agents.memory_agent import MemoryAgent, init_db as memory_init_db
from core.agents.web_agent import WebAgent
from core.config import settings
from core.modules.agent_router import AgentRouter, LLMConfig, ToolRegistry
from core.modules.gateway import GatewayConfig, NeronGateway
from core.modules.scheduler import setup as scheduler_setup
from core.modules.scheduler import start as scheduler_start
from core.modules.scheduler import stop as scheduler_stop
from core.modules.sessions import SessionStore
from core.modules.skills import SkillRegistry
from core.neron_time.time_provider import TimeProvider
from core.orchestrator.intent_router import Intent, IntentRouter
from core.agents.watchdog_agent import send_watchdog_notification, world_model
from core.agents.code_audit_agent import CodeAuditAgent
from core.agents.system_agent import handle_system_status

logger = get_logger("api_agent")

VERSION = "2.2.0"


# ── Helpers ───────────────────────────────────────────────────────────────────

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _personality_available() -> bool:
    try:
        import personality  # noqa: F401
        return True
    except ImportError:
        return False


# ── Prometheus ────────────────────────────────────────────────────────────────

def _counter(name, doc, labels=None):
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return Counter(name, doc, labels or [])

def _gauge(name, doc):
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return Gauge(name, doc)

def _histogram(name, doc, labels=None, buckets=None):
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    kwargs = {}
    if labels:   kwargs["labelnames"] = labels
    if buckets:  kwargs["buckets"]    = buckets
    return Histogram(name, doc, **kwargs)

_prom_requests_total  = _counter("neron_requests_total",     "Nombre total de requetes")
_prom_intent_total    = _counter("neron_intent_total",       "Requetes par intent",    ["intent"])
_prom_agent_errors    = _counter("neron_agent_errors_total", "Erreurs par agent",      ["agent"])
_prom_llm_calls       = _counter("neron_llm_calls_by_model", "Appels LLM par modele", ["model"])
_prom_requests_flight = _gauge("neron_requests_in_flight",   "Requetes en cours")
_prom_uptime          = _gauge("neron_uptime_seconds",       "Duree depuis le demarrage")
_prom_cpu             = _gauge("neron_system_cpu_percent",   "CPU systeme %")
_prom_ram             = _gauge("neron_system_ram_percent",   "RAM systeme %")
_prom_disk            = _gauge("neron_system_disk_percent",  "Disque systeme %")
_prom_process_ram     = _gauge("neron_process_ram_mb",       "RAM process Neron MB")
_prom_exec_time       = _histogram(
    "neron_execution_time_ms", "Temps orchestration ms",
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
)
_prom_agent_latency   = _histogram(
    "neron_agent_latency_ms", "Latence par agent ms",
    labels=["agent"],
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000],
)


class Metrics:
    def __init__(self, startup_time: float) -> None:
        self._startup_time = startup_time

    def record_request_start(self)                        -> None: _prom_requests_total.inc(); _prom_requests_flight.inc()
    def record_request_end(self, ms: float)               -> None: _prom_requests_flight.dec(); _prom_exec_time.observe(ms)
    def record_intent(self, intent: str)                  -> None: _prom_intent_total.labels(intent=intent).inc()
    def record_error(self, agent: str)                    -> None: _prom_agent_errors.labels(agent=agent).inc()
    def record_latency(self, agent: str, ms: float)       -> None: _prom_agent_latency.labels(agent=agent).observe(ms)
    def record_model_call(self, model: str)               -> None: model and _prom_llm_calls.labels(model=model).inc()

    def update_system_metrics(self) -> None:
        try:
            _prom_uptime.set(round(time.monotonic() - self._startup_time, 2))
            _prom_cpu.set(psutil.cpu_percent(interval=0.5))
            _prom_ram.set(psutil.virtual_memory().percent)
            _prom_disk.set(psutil.disk_usage("/").percent)
            _prom_process_ram.set(round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024))
        except Exception as e:
            logger.warning("update_system_metrics error : %s", e)

    def export(self) -> str:
        self.update_system_metrics()
        return generate_latest(REGISTRY).decode("utf-8")


# ── Pydantic models ───────────────────────────────────────────────────────────

class TextInput(BaseModel):
    text: str

class CoreResponse(BaseModel):
    response:          str
    intent:            str
    agent:             str
    confidence:        str
    timestamp:         str
    execution_time_ms: float
    model:             Optional[str] = None
    error:             Optional[str] = None
    transcription:     Optional[str] = None
    metadata:          dict          = {}


# ── APIAgent ──────────────────────────────────────────────────────────────────

class APIAgent(BaseAgent):
    """
    Agent FastAPI — expose les routes HTTP de Néron.
    Instancie et coordonne LLM, Web, Memory, HA, Code dans son propre process.
    """

    def __init__(self) -> None:
        super().__init__("api_agent")
        self._startup_time:  float               = 0.0
        self._gateway_task:  asyncio.Task | None = None
        self.metrics:        Metrics | None      = None

        # Agents métier — initialisés dans on_start()
        self.llm_agent:    LLMAgent    | None = None
        self.memory_agent: MemoryAgent | None = None
        self.web_agent:    WebAgent    | None = None
        self.ha_agent:     HAAgent     | None = None
        self.code_agent:       CodeAgent      | None = None
        self.code_audit_agent: CodeAuditAgent  | None = None
        self.router:           IntentRouter    | None = None
        self.time_provider: TimeProvider | None = None

        self._app: FastAPI | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def on_start(self) -> None:
        self._startup_time = time.monotonic()
        self.metrics       = Metrics(self._startup_time)
        logger.info(json.dumps({"event": "startup", "version": VERSION}))

        # Init agents métier
        self.llm_agent    = LLMAgent()
        self.web_agent    = WebAgent()
        self.ha_agent     = HAAgent()
        self.code_agent       = CodeAgent()
        self.code_audit_agent = CodeAuditAgent()
        memory_init_db()
        self.memory_agent = MemoryAgent()
        self.router        = IntentRouter(llm_agent=self.llm_agent)
        self.time_provider = TimeProvider()

        await self.ha_agent.on_start()

        if _personality_available():
            try:
                from personality import get_current_state
                state = get_current_state()
                logger.info(json.dumps({
                    "event":  "personality_loaded",
                    "mood":   state.get("mood"),
                    "energy": state.get("energy_level"),
                }))
            except Exception as e:
                logger.warning("Personality illisible : %s", e)
        else:
            logger.warning("Module personality non disponible — system prompt statique actif")

        # Scheduler
        scheduler_setup(
            agents={"code": self.code_agent, "memory": self.memory_agent},
            notify_fn=send_watchdog_notification,
        )
        scheduler_start()

        # Gateway WebSocket
        try:
            llm_cfg = LLMConfig(
                provider="ollama",
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_HOST,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
            )
            _sessions     = SessionStore()
            _skills       = SkillRegistry()
            _tools        = ToolRegistry().setup_defaults()
            _agent_router = AgentRouter(
                sessions=_sessions, skills=_skills,
                llm_config=llm_cfg, tools=_tools,
            )
            gw_config = GatewayConfig(
                host=settings.SERVER_HOST, port=18789,
                token=settings.API_KEY or None,
            )
            _gw = NeronGateway(
                config=gw_config, agent_router=_agent_router,
                session_store=_sessions, skill_registry=_skills,
            )
            self._gateway_task = asyncio.create_task(_gw.start())
            logger.info("Gateway WebSocket démarrée sur ws://0.0.0.0:18789")
        except Exception as e:
            logger.warning("Gateway WebSocket non démarrée : %s", e)

        logger.info(json.dumps({"event": "agents_ready"}))

    async def on_stop(self) -> None:
        scheduler_stop()

        if self.ha_agent:
            await self.ha_agent.on_stop()

        if self._gateway_task and not self._gateway_task.done():
            self._gateway_task.cancel()
            try:
                await self._gateway_task
            except asyncio.CancelledError:
                pass

        logger.info(json.dumps({"event": "shutdown"}))

    async def run(self) -> None:
        """Lance uvicorn dans la boucle de l'agent."""
        app = self._build_app()
        config = uvicorn.Config(
            app=app,
            host=settings.SERVER_HOST,
            port=settings.SERVER_PORT,
            log_level="warning",  # uvicorn silencieux — on gère nos propres logs
        )
        server = uvicorn.Server(config)
        await server.serve()

    # ── execute() — requis par BaseAgent ─────────────────────────────────────

    async def execute(self, query: str, **kwargs: Any) -> AgentResult:
        """Non utilisé directement — l'API passe par les routes HTTP."""
        return self._failure("APIAgent ne supporte pas execute() direct")

    # ── Construction FastAPI ──────────────────────────────────────────────────

    def _build_app(self) -> FastAPI:
        app = FastAPI(
            title="Neron Core",
            description="Orchestrateur central v" + VERSION,
            version=VERSION,
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

        async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> None:
            if not settings.API_KEY or settings.API_KEY == "changez_moi":
                return
            if api_key is None:
                raise HTTPException(status_code=401, detail="API Key manquante")
            if api_key != settings.API_KEY:
                raise HTTPException(status_code=403, detail="API Key invalide")

        # ── Routes système ────────────────────────────────────────────────────

        @app.get("/")
        def root():
            return {"service": "Neron Core", "version": VERSION, "status": "active"}

        @app.get("/health")
        def health():
            return {"status": "healthy", "version": VERSION}

        @app.get("/status")
        def status():
            try:
                return world_model.get()
            except Exception as e:
                raise HTTPException(500, f"Impossible de récupérer le status : {e}")

        @app.get("/status/agents")
        async def agents_status(_: None = Depends(verify_api_key)):
            from core.world_model.publisher import read_all
            return {"agents": read_all(), "timestamp": utc_now_iso()}

        @app.get("/metrics")
        def prometheus_metrics():
            from fastapi.responses import Response
            return Response(content=self.metrics.export(), media_type=CONTENT_TYPE_LATEST)

        @app.post("/ha/reload")
        async def ha_reload(_: None = Depends(verify_api_key)):
            if not self.ha_agent:
                raise HTTPException(503, "Agent HA non disponible")
            count = await self.ha_agent.reload()
            return {"status": "ok", "entities": count, "timestamp": utc_now_iso()}

        # ── Routes /personality ───────────────────────────────────────────────

        @app.get("/personality/state")
        async def personality_state(_: None = Depends(verify_api_key)):
            if not _personality_available():
                raise HTTPException(503, "Module personality non disponible")
            try:
                from personality import get_current_state
                return {"status": "ok", "state": get_current_state(), "timestamp": utc_now_iso()}
            except Exception as e:
                raise HTTPException(500, f"Erreur lecture état personality : {e}")

        @app.get("/personality/history")
        async def personality_history(limit: int = 20, _: None = Depends(verify_api_key)):
            if not _personality_available():
                raise HTTPException(503, "Module personality non disponible")
            limit = min(max(1, limit), 100)
            try:
                from personality import get_history
                history = get_history(limit=limit)
                return {"status": "ok", "history": history, "count": len(history), "timestamp": utc_now_iso()}
            except Exception as e:
                raise HTTPException(500, f"Erreur lecture historique personality : {e}")

        @app.post("/personality/reset")
        async def personality_reset(_: None = Depends(verify_api_key)):
            if not _personality_available():
                raise HTTPException(503, "Module personality non disponible")
            try:
                from personality import force_update
                from personality.updater import _resolve_protected
                results = [
                    force_update(None, "mood",         "neutre", "reset via API"),
                    force_update(None, "energy_level", "normal", "reset via API"),
                ]
                _resolve_protected.cache_clear()
                return {"status": "ok", "reset": ["mood", "energy_level"], "results": results, "timestamp": utc_now_iso()}
            except Exception as e:
                raise HTTPException(500, f"Erreur reset personality : {e}")

        # ── Routes /input ─────────────────────────────────────────────────────

        @app.post("/input/text", response_model=CoreResponse)
        async def text_input(input_data: TextInput, _: None = Depends(verify_api_key)):
            return await self._handle_text(input_data.text.strip())

        @app.post("/input/stream")
        async def text_input_stream(input_data: TextInput, _: None = Depends(verify_api_key)):
            return StreamingResponse(
                self._stream(input_data.text.strip()),
                media_type="text/event-stream",
            )

        @app.post("/input/audio", response_model=CoreResponse)
        async def audio_input(file: UploadFile = File(...)):
            return await self._handle_audio(file)

        @app.post("/input/voice")
        async def voice_input(file: UploadFile = File(...)):
            return await self._handle_voice(file)

        # ── Routes /system ────────────────────────────────────────────────────

        @app.get("/system/status")
        async def system_status(q: str = "general", _: None = Depends(verify_api_key)):
            result = await handle_system_status(q)
            return {"status": "ok", "response": result, "timestamp": utc_now_iso()}

        # ── Routes /code/audit ────────────────────────────────────────────────

        @app.post("/code/audit/file")
        async def audit_file(data: TextInput, _: None = Depends(verify_api_key)):
            result = await self.code_audit_agent.execute(
                "", action="audit_file", path=data.text
            )
            return {
                "success":  result.success,
                "response": result.content,
                "metadata": result.metadata,
                "error":    result.error,
            }

        @app.post("/code/audit/folder")
        async def audit_folder(data: TextInput, _: None = Depends(verify_api_key)):
            result = await self.code_audit_agent.execute(
                "", action="audit_folder", folder=data.text
            )
            return {
                "success":  result.success,
                "response": result.content,
                "metadata": result.metadata,
                "error":    result.error,
            }

        @app.post("/code/audit/all")
        async def audit_all(_: None = Depends(verify_api_key)):
            result = await self.code_audit_agent.execute("", action="audit_all")
            return {
                "success":  result.success,
                "response": result.content,
                "metadata": result.metadata,
                "error":    result.error,
            }

        return app

    # ── Pipeline texte ────────────────────────────────────────────────────────

    async def _handle_text(self, query: str) -> CoreResponse:
        start = time.monotonic()
        self.metrics.record_request_start()
        logger.info(json.dumps({"event": "request_received", "query": query[:80]}))

        intent_result = await self.router.route(query)
        self.metrics.record_intent(intent_result.intent.value)
        metadata = {"intent": intent_result.intent.value, "confidence": intent_result.confidence}

        try:
            if intent_result.intent == Intent.PERSONALITY_FEEDBACK:
                return await self._handle_personality_feedback(query, intent_result, metadata, start)
            elif intent_result.intent == Intent.TIME_QUERY:
                return self._handle_time_query(intent_result, metadata, start, query)
            elif intent_result.intent == Intent.WEB_SEARCH:
                return await self._handle_web_search(query, intent_result, metadata, start)
            elif intent_result.intent == Intent.HA_ACTION:
                return await self._handle_ha_action(query, intent_result, metadata, start)
            elif intent_result.intent == Intent.CODE:
                return await self._handle_code(query, intent_result, metadata, start)
            else:
                return await self._handle_conversation(query, intent_result, metadata, start)
        finally:
            self.metrics.record_request_end(round((time.monotonic() - start) * 1000, 2))

    async def _stream(self, query: str):
        try:
            intent_result = await self.router.route(query)
            if intent_result.intent == Intent.PERSONALITY_FEEDBACK:
                result = await self._handle_personality_feedback(query, intent_result, {}, 0)
                yield f"data: {json.dumps({'token': result.response, 'done': True})}\n\n"
                return
            if intent_result.intent == Intent.TIME_QUERY:
                response = self._handle_time_query(intent_result, {}, 0, query).response
                yield f"data: {json.dumps({'token': response, 'done': True})}\n\n"
                return

            memory_context = await self._get_memory_context(query)
            full_response  = ""
            async for token in self.llm_agent.stream(query, context_data=memory_context or None):
                full_response += token
                yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"

            await self._store_memory(query, full_response, {"intent": intent_result.intent.value})
            yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
        except Exception as e:
            logger.exception("stream exception : %s", e)
            yield f"data: {json.dumps({'token': '', 'done': True, 'error': str(e)})}\n\n"

    async def _handle_audio(self, file: UploadFile) -> CoreResponse:
        start = time.monotonic()
        self.metrics.record_request_start()
        try:
            from core.agents.stt_agent import STTAgent
            stt = STTAgent()
            audio_bytes = await file.read()
            result      = await stt.transcribe(audio_bytes, file.filename)
            if not result.success:
                self.metrics.record_error("stt_agent")
                raise HTTPException(503, f"STT indisponible : {result.error}")
            if result.latency_ms:
                self.metrics.record_latency("stt_agent", result.latency_ms)
            core_response               = await self._handle_text(result.content)
            core_response.transcription = result.content
            core_response.metadata["stt"] = {
                "language": result.metadata.get("language"),
                "stt_latency_ms": result.latency_ms,
            }
            return core_response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Erreur pipeline audio : {e}")
        finally:
            self.metrics.record_request_end(round((time.monotonic() - start) * 1000, 2))

    async def _handle_voice(self, file: UploadFile):
        from fastapi.responses import Response as FastAPIResponse
        from core.agents.stt_agent import STTAgent
        from core.agents.tts_agent import TTSAgent
        start = time.monotonic()
        self.metrics.record_request_start()
        try:
            stt         = STTAgent()
            tts         = TTSAgent()
            audio_bytes = await file.read()
            stt_result  = await stt.transcribe(audio_bytes, file.filename)
            if not stt_result.success:
                self.metrics.record_error("stt_agent")
                raise HTTPException(503, f"STT indisponible : {stt_result.error}")
            if stt_result.latency_ms:
                self.metrics.record_latency("stt_agent", stt_result.latency_ms)
            if not stt_result.content:
                raise HTTPException(400, "Transcription vide")
            core_response = await self._handle_text(stt_result.content)
            tts_result    = await tts.synthesize(core_response.response)
            if not tts_result.success:
                self.metrics.record_error("tts_agent")
                return core_response
            if tts_result.latency_ms:
                self.metrics.record_latency("tts_agent", tts_result.latency_ms)
            return FastAPIResponse(
                content=tts_result.metadata["audio_bytes"],
                media_type=tts_result.metadata.get("mimetype", "audio/wav"),
                headers={
                    "X-Transcription":     stt_result.content[:200].encode("ascii", "replace").decode(),
                    "X-Response-Text":     core_response.response[:200].encode("ascii", "replace").decode(),
                    "X-Intent":            core_response.intent,
                    "X-Execution-Time-Ms": str(round((time.monotonic() - start) * 1000, 2)),
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Erreur pipeline vocal : {e}")
        finally:
            self.metrics.record_request_end(round((time.monotonic() - start) * 1000, 2))

    # ── Handlers intent ───────────────────────────────────────────────────────

    async def _get_memory_context(self, query: str) -> str:
        try:
            recent = self.memory_agent.retrieve(limit=1)
            if recent:
                e = recent[0]
                return f"Echange précédent:\nUtilisateur: {e['input']}\nNeron: {e['response'][:120]}"
        except Exception as e:
            logger.warning("memory_context_failed : %s", e)
        return ""

    async def _store_memory(self, query: str, response: str, metadata: dict) -> None:
        try:
            self.memory_agent.store(query, response, metadata)
        except Exception as e:
            logger.warning("memory_store_failed : %s", e)

    async def _handle_conversation(self, query, intent_result, metadata, start) -> CoreResponse:
        # Détection requête système
        if any(w in query.lower() for w in ["cpu", "ram", "disque", "santé", "anomalie", "système"]):
            response = await handle_system_status(query)
            await self._store_memory(query, response, metadata)
            return CoreResponse(
                response=response, intent="system_status", agent="system_agent",
                confidence="high", timestamp=utc_now_iso(),
                execution_time_ms=round((time.monotonic() - start) * 1000, 2),
                metadata=metadata,
            )

        memory_context = await self._get_memory_context(query)
        result = await self.llm_agent.execute(query, context_data=memory_context or None)
        if not result.success:
            self.metrics.record_error("llm_agent")
            raise HTTPException(503, f"LLM indisponible : {result.error}")
        if result.latency_ms:
            self.metrics.record_latency("llm_agent", result.latency_ms)
        model = result.metadata.get("model")
        self.metrics.record_model_call(model)
        await self._store_memory(query, result.content, metadata)
        return CoreResponse(
            response=result.content, intent=metadata.get("intent", "conversation"),
            agent="llm_agent", confidence=metadata.get("confidence", "low"),
            timestamp=utc_now_iso(),
            execution_time_ms=round((time.monotonic() - start) * 1000, 2),
            model=model, metadata={**metadata, **result.metadata},
        )

    async def _handle_web_search(self, query, intent_result, metadata, start) -> CoreResponse:
        web_result = await self.web_agent.execute(query)
        if not web_result.success:
            self.metrics.record_error("web_agent")
            return await self._handle_conversation(query, intent_result, metadata, start)
        if web_result.latency_ms:
            self.metrics.record_latency("web_agent", web_result.latency_ms)
        llm_result = await self.llm_agent.execute(query=query, context_data=web_result.content)
        if not llm_result.success:
            self.metrics.record_error("llm_agent")
            response_text, model = web_result.content, None
        else:
            response_text = llm_result.content
            model         = llm_result.metadata.get("model")
            self.metrics.record_model_call(model)
            if llm_result.latency_ms:
                self.metrics.record_latency("llm_agent", llm_result.latency_ms)
        metadata["web_sources"] = web_result.metadata.get("sources", [])
        await self._store_memory(query, response_text, metadata)
        return CoreResponse(
            response=response_text, intent="web_search", agent="web_agent+llm_agent",
            confidence=intent_result.confidence, timestamp=utc_now_iso(),
            execution_time_ms=round((time.monotonic() - start) * 1000, 2),
            model=model, metadata={**metadata, **(llm_result.metadata if llm_result.success else {})},
        )

    async def _handle_ha_action(self, query, intent_result, metadata, start) -> CoreResponse:
        result  = await self.ha_agent.execute(query)
        elapsed = round((time.monotonic() - start) * 1000, 2)
        if result.success:
            return CoreResponse(
                response=result.content, intent=intent_result.intent.value, agent="ha_agent",
                confidence=intent_result.confidence, timestamp=utc_now_iso(),
                execution_time_ms=elapsed, metadata=result.metadata,
            )
        return CoreResponse(
            response=f"Je n'ai pas pu exécuter cette action : {result.error}",
            intent=intent_result.intent.value, agent="ha_agent",
            confidence=intent_result.confidence, timestamp=utc_now_iso(),
            execution_time_ms=elapsed, error=result.error, metadata={},
        )

    async def _handle_code(self, query, intent_result, metadata, start) -> CoreResponse:
        path_match = re.search(r"(\S+\.py)", query)
        path       = path_match.group(1) if path_match else ""
        if not path:
            def _norm(t):
                n = unicodedata.normalize("NFD", t.lower())
                return "".join(c for c in n if unicodedata.category(c) != "Mn")
            stop = {
                "un", "une", "le", "la", "les", "de", "du", "des", "qui", "pour",
                "que", "moi", "me", "genere", "cree", "ecris", "script", "fichier",
                "module", "python", "code", "affiche", "bonjour", "donne",
            }
            words      = re.findall(r"[a-z0-9]+", _norm(query))
            name_words = [w for w in words if w not in stop][:3]
            path       = "_".join(name_words) + ".py" if name_words else "script.py"
        result            = await self.code_agent.execute(query, path=path)
        execution_time_ms = round((time.monotonic() - start) * 1000, 2)
        if not result.success:
            self.metrics.record_error("code_agent")
            return CoreResponse(
                response=f"Je n'ai pas pu exécuter cette action : {result.error}",
                intent="code", agent="code_agent", confidence=intent_result.confidence,
                timestamp=utc_now_iso(), execution_time_ms=execution_time_ms,
                error=result.error, metadata={},
            )
        self.metrics.record_latency("code_agent", result.latency_ms or 0)
        return CoreResponse(
            response=result.content, intent="code", agent="code_agent",
            confidence=intent_result.confidence, timestamp=utc_now_iso(),
            execution_time_ms=execution_time_ms, metadata=result.metadata,
        )

    async def _handle_personality_feedback(self, query, intent_result, metadata, start) -> CoreResponse:
        elapsed = round((time.monotonic() - start) * 1000, 2)
        if not _personality_available():
            return CoreResponse(
                response="Je n'ai pas pu mettre à jour ma personnalité (module non disponible).",
                intent="personality_feedback", agent="personality",
                confidence=intent_result.confidence, timestamp=utc_now_iso(),
                execution_time_ms=elapsed, metadata=metadata,
            )
        try:
            from personality import update_from_feedback
            result = update_from_feedback(query)
            if result["status"] == "updated" and result["changes"]:
                parts    = [f"{c['field']} -> {c['new_value']}" for c in result["changes"]]
                response = "Compris. J'ai adapté mon comportement : " + ", ".join(parts) + "."
                logger.info(json.dumps({"event": "personality_updated", "changes": result["changes"]}))
            else:
                response = "Message reçu, mais aucun changement de comportement n'a été nécessaire."
            return CoreResponse(
                response=response, intent="personality_feedback", agent="personality",
                confidence=intent_result.confidence, timestamp=utc_now_iso(),
                execution_time_ms=elapsed,
                metadata={**metadata, "personality_changes": result.get("changes", [])},
            )
        except Exception as e:
            logger.error("personality update_from_feedback échoué : %s", e)
            return CoreResponse(
                response="Je n'ai pas pu appliquer ce changement de comportement.",
                intent="personality_feedback", agent="personality",
                confidence=intent_result.confidence, timestamp=utc_now_iso(),
                execution_time_ms=elapsed, error=str(e), metadata=metadata,
            )

    def _handle_time_query(self, intent_result, metadata, start, query="") -> CoreResponse:
        q          = query.lower()
        heure_keys = ["heure", "time", "il est", "quelle heure"]
        date_keys  = ["quelle date sommes", "on est quel jour", "quel jour sommes",
                      "quel mois sommes", "donne moi la date", "c est quoi la date", "on est le combien"]
        want_heure = any(k in q for k in heure_keys)
        want_date  = any(k in q for k in date_keys)
        n = self.time_provider.now()
        from neron_time.time_provider import JOURS, MOIS
        jour = JOURS[n.weekday()]
        mois = MOIS[n.month - 1]
        if want_heure and not want_date:
            response = f"Il est {n.hour:02d}h{n.minute:02d}."
        elif want_date and not want_heure:
            response = f"Nous sommes {jour} {n.day} {mois} {n.year}."
        else:
            response = f"Il est {n.hour:02d}h{n.minute:02d}, {jour} {n.day} {mois} {n.year}."
        return CoreResponse(
            response=response, intent="time_query", agent="time_provider",
            confidence=intent_result.confidence, timestamp=utc_now_iso(),
            execution_time_ms=round((time.monotonic() - start) * 1000, 2),
            metadata={**metadata, "iso": self.time_provider.iso(), "timestamp": self.time_provider.timestamp()},
        )
