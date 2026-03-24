# core/app.py
# Neron Core v2.2.0

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import unicodedata
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Security, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from agents.base_agent import get_logger
from agents.code_agent import CodeAgent
from agents.ha_agent import HAAgent
from agents.llm_agent import LLMAgent
from agents.memory_agent import MemoryAgent, init_db as memory_init_db
from agents.stt_agent import STTAgent, load_model as stt_load_model
from agents.telegram_agent import send_notification, set_agents, start_bot, stop_bot
from agents.tts_agent import TTSAgent, load_engine as tts_load_engine
from agents.watchdog_agent import (
    send_watchdog_notification,
    setup as watchdog_setup,
    start_watchdog,
    start_watchdog_bot,
    stop_watchdog,
    stop_watchdog_bot,
)
from agents.web_agent import WebAgent
from config import settings

# FIX: imports modules.* dédupliqués — un seul bloc
from modules.agent_router import AgentRouter, LLMConfig, ToolRegistry
from modules.gateway import GatewayConfig, NeronGateway
from modules.scheduler import setup as scheduler_setup
from modules.scheduler import start as scheduler_start
from modules.scheduler import stop as scheduler_stop
from modules.sessions import SessionStore
from modules.skills import SkillRegistry
from neron_time.time_provider import TimeProvider
from orchestrator.intent_router import Intent, IntentRouter

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(level=settings.LOG_LEVEL)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
_log_file     = settings.LOGS_DIR / settings.LOG_NERON
_file_handler = logging.FileHandler(_log_file)
_file_handler.setLevel(settings.LOG_LEVEL)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logging.getLogger().addHandler(_file_handler)
logger = get_logger("neron_core")

VERSION = "2.2.0"

# ── État global ───────────────────────────────────────────────────────────────

_startup_time:  float          = 0.0
_gateway_task:  asyncio.Task | None = None  # FIX: déclaré au niveau module

llm_agent:     LLMAgent      | None = None
memory_agent:  MemoryAgent   | None = None
web_agent:     WebAgent      | None = None
stt_agent:     STTAgent      | None = None
tts_agent:                    None  = None
ha_agent:      HAAgent       | None = None
code_agent:    CodeAgent     | None = None
router:        IntentRouter  | None = None
time_provider: TimeProvider  | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Module personality ────────────────────────────────────────────────────────

def _personality_available() -> bool:
    try:
        import personality  # noqa: F401
        return True
    except ImportError:
        return False


# ── Metrics ───────────────────────────────────────────────────────────────────

class Metrics:
    def __init__(self) -> None:
        self._intent_counts:      dict  = {}
        self._agent_errors:       dict  = {}
        self._latencies:          dict  = {}
        self._requests_total:     int   = 0
        self._requests_in_flight: int   = 0
        self._execution_times:    list  = []
        self._model_calls:        dict  = {}

    def record_request_start(self) -> None:
        self._requests_total     += 1
        self._requests_in_flight += 1

    def record_request_end(self, execution_time_ms: float) -> None:
        self._requests_in_flight = max(0, self._requests_in_flight - 1)
        self._execution_times.append(execution_time_ms)
        if len(self._execution_times) > 1000:
            self._execution_times = self._execution_times[-1000:]

    def record_intent(self, intent: str) -> None:
        self._intent_counts[intent] = self._intent_counts.get(intent, 0) + 1

    def record_error(self, agent: str) -> None:
        self._agent_errors[agent] = self._agent_errors.get(agent, 0) + 1

    def record_latency(self, agent: str, latency_ms: float) -> None:
        self._latencies.setdefault(agent, []).append(latency_ms)
        if len(self._latencies[agent]) > 1000:
            self._latencies[agent] = self._latencies[agent][-1000:]

    def record_model_call(self, model: str) -> None:
        if model:
            self._model_calls[model] = self._model_calls.get(model, 0) + 1

    def export(self) -> str:
        lines  = []
        uptime = round(time.monotonic() - _startup_time, 2)
        lines += [
            "# HELP neron_uptime_seconds Duree depuis le demarrage",
            "# TYPE neron_uptime_seconds gauge",
            f"neron_uptime_seconds {uptime}",
            "# HELP neron_requests_total Nombre total de requetes",
            "# TYPE neron_requests_total counter",
            f"neron_requests_total {self._requests_total}",
            "# HELP neron_requests_in_flight Requetes en cours",
            "# TYPE neron_requests_in_flight gauge",
            f"neron_requests_in_flight {self._requests_in_flight}",
        ]
        if self._execution_times:
            avg = round(sum(self._execution_times) / len(self._execution_times), 2)
            lines += [
                "# HELP neron_execution_time_avg_ms Temps moyen orchestration (ms)",
                "# TYPE neron_execution_time_avg_ms gauge",
                f"neron_execution_time_avg_ms {avg}",
            ]
        lines += [
            "# HELP neron_intent_total Requetes par intent",
            "# TYPE neron_intent_total counter",
        ]
        for intent, count in self._intent_counts.items():
            lines.append(f'neron_intent_total{{intent="{intent}"}} {count}')
        lines += [
            "# HELP neron_agent_errors_total Erreurs par agent",
            "# TYPE neron_agent_errors_total counter",
        ]
        for agent, count in self._agent_errors.items():
            lines.append(f'neron_agent_errors_total{{agent="{agent}"}} {count}')
        lines += [
            "# HELP neron_agent_latency_avg_ms Latence moyenne par agent (ms)",
            "# TYPE neron_agent_latency_avg_ms gauge",
        ]
        for agent, values in self._latencies.items():
            avg = round(sum(values) / len(values), 2)
            lines.append(f'neron_agent_latency_avg_ms{{agent="{agent}"}} {avg}')
        lines += [
            "# HELP neron_llm_calls_by_model Appels LLM par modele",
            "# TYPE neron_llm_calls_by_model counter",
        ]
        for model, count in self._model_calls.items():
            lines.append(f'neron_llm_calls_by_model{{model="{model}"}} {count}')
        return "\n".join(lines) + "\n"


metrics = Metrics()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_agent, web_agent, stt_agent, tts_agent, ha_agent
    global router, time_provider, _startup_time, memory_agent
    global code_agent, _gateway_task

    _startup_time = time.monotonic()
    logger.info(json.dumps({"event": "startup", "version": VERSION}))

    llm_agent = LLMAgent()
    web_agent = WebAgent()
    memory_init_db()
    memory_agent = MemoryAgent()
    # STT/TTS désactivés — pipeline voix supprimé avec NEXUS avatar 3D
    # stt_load_model()
    # stt_agent = STTAgent()
    # tts_load_engine()
    # tts_agent  = TTSAgent()
    ha_agent   = HAAgent()
    code_agent = CodeAgent()

    await ha_agent.on_start()
    router        = IntentRouter(llm_agent=llm_agent)
    time_provider = TimeProvider()

    if _personality_available():
        try:
            from personality import get_current_state
            state = get_current_state()
            logger.info(json.dumps({
                "event":  "personality_loaded",
                "mood":   state.get("mood"),
                "energy": state.get("energy_level"),
                "tone":   state.get("communication", {}).get("tone"),
            }))
        except Exception as e:
            logger.warning("Personality chargé mais état illisible : %s", e)
    else:
        logger.warning("Module personality non disponible — system prompt statique actif")

    logger.info(json.dumps({"event": "agents_ready"}))

    # ── Scheduler ──
    scheduler_setup(
        agents={"code": code_agent, "memory": memory_agent},
        notify_fn=send_watchdog_notification,
    )
    scheduler_start()

    # ── Gateway WebSocket ──
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
            sessions=_sessions,
            skills=_skills,
            llm_config=llm_cfg,
            tools=_tools,
        )
        gw_config = GatewayConfig(
            host=settings.SERVER_HOST,
            port=18789,
            token=settings.API_KEY or None,
        )
        _gw = NeronGateway(
            config=gw_config,
            agent_router=_agent_router,
            session_store=_sessions,
            skill_registry=_skills,
        )
        _gateway_task = asyncio.create_task(_gw.start())
        logger.info("Gateway WebSocket démarré sur ws://0.0.0.0:18789")
    except Exception as e:
        logger.warning("Gateway WebSocket non démarré : %s", e)

    # FIX: tabulation mixte supprimée dans le dict set_agents
    set_agents({
        "llm":    llm_agent,
        "stt":    stt_agent,
        "tts":    tts_agent,
        "memory": memory_agent,
        "ha":     ha_agent,
        "code":   code_agent,
    })

    telegram_enabled = getattr(settings, "TELEGRAM_ENABLED", False)
    telegram_token   = getattr(settings, "TELEGRAM_BOT_TOKEN", "")

    if telegram_enabled and telegram_token not in ("", "votre_token_ici", None):
        try:
            await start_bot()
        except Exception as e:
            logger.warning("Impossible de démarrer Telegram : %s", e)
    else:
        logger.info("Telegram désactivé ou token non configuré")

    if getattr(settings, "WATCHDOG_ENABLED", False):
        watchdog_setup(
            agents={"llm": llm_agent, "stt": stt_agent, "tts": tts_agent},
            notify_fn=send_watchdog_notification,
        )
        await start_watchdog()
        await start_watchdog_bot()

    yield

    # ── Shutdown ──
    scheduler_stop()
    await ha_agent.on_stop()

    if _gateway_task and not _gateway_task.done():
        _gateway_task.cancel()
        try:
            await _gateway_task
        except asyncio.CancelledError:
            pass

    if getattr(settings, "WATCHDOG_ENABLED", False):
        await stop_watchdog_bot()
        await stop_watchdog()

    if telegram_enabled and telegram_token not in ("", "votre_token_ici", None):
        try:
            await stop_bot()
        except Exception as e:
            logger.warning("Impossible d'arrêter Telegram : %s", e)

    logger.info(json.dumps({"event": "shutdown"}))


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Neron Core",
    description="Orchestrateur central - v" + VERSION,
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

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


# ── Auth ──────────────────────────────────────────────────────────────────────

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> None:
    if not settings.API_KEY or settings.API_KEY == "changez_moi":
        return
    if api_key is None:
        raise HTTPException(status_code=401, detail="API Key manquante")
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="API Key invalide")


# ── Routes système ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"service": "Neron Core", "version": VERSION, "status": "active"}


@app.get("/health")
def health():
    return {"status": "healthy", "version": VERSION}


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return PlainTextResponse(metrics.export(), media_type="text/plain")


@app.post("/ha/reload")
async def ha_reload(_: None = Depends(verify_api_key)):
    if not ha_agent:
        raise HTTPException(503, "Agent HA non disponible")
    count = await ha_agent.reload()
    return {"status": "ok", "entities": count, "timestamp": utc_now_iso()}


# ── Routes /personality ───────────────────────────────────────────────────────

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
async def personality_history(
    limit: int = 20,
    _: None = Depends(verify_api_key),
):
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
        return {
            "status":    "ok",
            "reset":     ["mood", "energy_level"],
            "results":   results,
            "timestamp": utc_now_iso(),
        }
    except Exception as e:
        raise HTTPException(500, f"Erreur reset personality : {e}")


# ── Routes /input ─────────────────────────────────────────────────────────────

@app.post("/input/text", response_model=CoreResponse)
async def text_input(
    input_data: TextInput,
    _: None = Depends(verify_api_key),
):
    query = input_data.text.strip()
    start = time.monotonic()
    metrics.record_request_start()
    logger.info(json.dumps({"event": "request_received", "query": query[:80]}))

    intent_result = await router.route(query)
    metrics.record_intent(intent_result.intent.value)

    metadata = {
        "intent":     intent_result.intent.value,
        "confidence": intent_result.confidence,
    }

    try:
        if intent_result.intent == Intent.PERSONALITY_FEEDBACK:
            return await _handle_personality_feedback(query, intent_result, metadata, start)
        elif intent_result.intent == Intent.TIME_QUERY:
            return _handle_time_query(intent_result, metadata, start, query)
        elif intent_result.intent == Intent.WEB_SEARCH:
            return await _handle_web_search(query, intent_result, metadata, start)
        elif intent_result.intent == Intent.HA_ACTION:
            return await _handle_ha_action(query, intent_result, metadata, start)
        elif intent_result.intent == Intent.CODE:
            return await _handle_code(query, intent_result, metadata, start)
        else:
            return await _handle_conversation(query, intent_result, metadata, start)
    finally:
        elapsed = round((time.monotonic() - start) * 1000, 2)
        metrics.record_request_end(elapsed)


@app.post("/input/stream")
async def text_input_stream(
    input_data: TextInput,
    _: None = Depends(verify_api_key),
):
    query = input_data.text.strip()

    async def generate():
        try:
            intent_result = await router.route(query)
            logger.debug("stream: intent=%s", intent_result.intent.value)

            # Intents non-streamables → réponse directe encapsulée
            if intent_result.intent == Intent.PERSONALITY_FEEDBACK:
                result = await _handle_personality_feedback(query, intent_result, {}, 0)
                yield f"data: {json.dumps({'token': result.response, 'done': True})}\n\n"
                return

            if intent_result.intent == Intent.TIME_QUERY:
                response = _handle_time_query(intent_result, {}, 0, query).response
                yield f"data: {json.dumps({'token': response, 'done': True})}\n\n"
                return

            memory_context = await _get_memory_context(query)
            full_response  = ""
            token_count    = 0

            async for token in llm_agent.stream(
                query, context_data=memory_context or None
            ):
                full_response += token
                token_count   += 1
                yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"

            logger.debug("stream: %d tokens reçus, sauvegarde mémoire", token_count)
            await _store_memory(query, full_response, {"intent": intent_result.intent.value})

            logger.debug("stream: envoi done")
            yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
            logger.debug("stream: terminé proprement")

        except Exception as e:
            logger.exception("stream: exception dans generate() : %s", e)
            yield f"data: {json.dumps({'token': '', 'done': True, 'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/input/audio", response_model=CoreResponse)
async def audio_input(file: UploadFile = File(...)):
    start = time.monotonic()
    metrics.record_request_start()
    try:
        audio_bytes = await file.read()
        result      = await stt_agent.transcribe(audio_bytes, file.filename)

        if not result.success:
            metrics.record_error("stt_agent")
            raise HTTPException(503, f"STT indisponible : {result.error}")

        if result.latency_ms:
            metrics.record_latency("stt_agent", result.latency_ms)

        transcription          = result.content
        core_response          = await text_input(TextInput(text=transcription))
        core_response.transcription = transcription
        core_response.metadata["stt"] = {
            "language":       result.metadata.get("language"),
            "stt_latency_ms": result.latency_ms,
        }
        return core_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur pipeline audio : {e}")
    finally:
        elapsed = round((time.monotonic() - start) * 1000, 2)
        metrics.record_request_end(elapsed)


@app.post("/input/voice")
async def voice_input(file: UploadFile = File(...)):
    from fastapi.responses import Response as FastAPIResponse

    start = time.monotonic()
    metrics.record_request_start()
    try:
        audio_bytes   = await file.read()
        stt_result    = await stt_agent.transcribe(audio_bytes, file.filename)

        if not stt_result.success:
            metrics.record_error("stt_agent")
            raise HTTPException(503, f"STT indisponible : {stt_result.error}")

        if stt_result.latency_ms:
            metrics.record_latency("stt_agent", stt_result.latency_ms)

        transcription = stt_result.content
        if not transcription:
            raise HTTPException(400, "Transcription vide")

        core_response = await text_input(TextInput(text=transcription))
        tts_result    = await tts_agent.synthesize(core_response.response)

        if not tts_result.success:
            metrics.record_error("tts_agent")
            return core_response

        if tts_result.latency_ms:
            metrics.record_latency("tts_agent", tts_result.latency_ms)

        execution_time_ms = round((time.monotonic() - start) * 1000, 2)
        return FastAPIResponse(
            content=tts_result.metadata["audio_bytes"],
            media_type=tts_result.metadata.get("mimetype", "audio/wav"),
            headers={
                "X-Transcription":     transcription[:200].encode("ascii", "replace").decode(),
                "X-Response-Text":     core_response.response[:200].encode("ascii", "replace").decode(),
                "X-Intent":            core_response.intent,
                "X-Execution-Time-Ms": str(execution_time_ms),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur pipeline vocal : {e}")
    finally:
        elapsed = round((time.monotonic() - start) * 1000, 2)
        metrics.record_request_end(elapsed)


# ── Handlers internes ─────────────────────────────────────────────────────────

async def _handle_personality_feedback(
    query: str, intent_result, metadata: dict, start: float
) -> CoreResponse:
    execution_time_ms = round((time.monotonic() - start) * 1000, 2)

    if not _personality_available():
        return CoreResponse(
            response="Je n'ai pas pu mettre à jour ma personnalité (module non disponible).",
            intent="personality_feedback",
            agent="personality",
            confidence=intent_result.confidence,
            timestamp=utc_now_iso(),
            execution_time_ms=execution_time_ms,
            metadata=metadata,
        )

    try:
        from personality import update_from_feedback
        result = update_from_feedback(query)

        if result["status"] == "updated" and result["changes"]:
            parts    = [f"{c['field']} → {c['new_value']}" for c in result["changes"]]
            response = "Compris. J'ai adapté mon comportement : " + ", ".join(parts) + "."
            logger.info(json.dumps({
                "event":   "personality_updated",
                "changes": result["changes"],
            }))
        else:
            response = "Message reçu, mais aucun changement de comportement n'a été nécessaire."

        return CoreResponse(
            response=response,
            intent="personality_feedback",
            agent="personality",
            confidence=intent_result.confidence,
            timestamp=utc_now_iso(),
            execution_time_ms=execution_time_ms,
            metadata={**metadata, "personality_changes": result.get("changes", [])},
        )
    except Exception as e:
        logger.error("personality update_from_feedback échoué : %s", e)
        return CoreResponse(
            response="Je n'ai pas pu appliquer ce changement de comportement.",
            intent="personality_feedback",
            agent="personality",
            confidence=intent_result.confidence,
            timestamp=utc_now_iso(),
            execution_time_ms=execution_time_ms,
            error=str(e),
            metadata=metadata,
        )


def _handle_time_query(
    intent_result, metadata: dict, start: float, query: str = ""
) -> CoreResponse:
    q          = query.lower()
    heure_keys = ["heure", "time", "il est", "quelle heure"]
    date_keys  = [
        "quelle date sommes", "on est quel jour", "quel jour sommes",
        "quel mois sommes", "donne moi la date", "c est quoi la date",
        "on est le combien",
    ]
    want_heure = any(k in q for k in heure_keys)
    want_date  = any(k in q for k in date_keys)

    n = time_provider.now()
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
        response=response,
        intent="time_query",
        agent="time_provider",
        confidence=intent_result.confidence,
        timestamp=utc_now_iso(),
        execution_time_ms=round((time.monotonic() - start) * 1000, 2),
        metadata={**metadata, "iso": time_provider.iso(), "timestamp": time_provider.timestamp()},
    )


async def _get_memory_context(query: str) -> str:
    try:
        recent = memory_agent.retrieve(limit=1)
        if recent:
            entry = recent[0]
            return (
                f"Échange précédent:\n"
                f"Utilisateur: {entry['input']}\n"
                f"Neron: {entry['response'][:120]}"
            )
    except Exception as e:
        logger.warning(json.dumps({"event": "memory_context_failed", "error": str(e)}))
    return ""


async def _store_memory(query: str, response: str, metadata: dict) -> None:
    try:
        memory_agent.store(query, response, metadata)
    except Exception as e:
        logger.warning(json.dumps({"event": "memory_store_failed", "error": str(e)}))


async def _handle_conversation(
    query: str, intent_result, metadata: dict, start: float
) -> CoreResponse:
    memory_context = await _get_memory_context(query)
    result = await llm_agent.execute(
        query, context_data=memory_context if memory_context else None
    )

    if not result.success:
        metrics.record_error("llm_agent")
        raise HTTPException(503, f"LLM indisponible : {result.error}")

    if result.latency_ms:
        metrics.record_latency("llm_agent", result.latency_ms)

    model = result.metadata.get("model")
    metrics.record_model_call(model)
    await _store_memory(query, result.content, metadata)

    return CoreResponse(
        response=result.content,
        intent=metadata.get("intent", "conversation"),
        agent="llm_agent",
        confidence=metadata.get("confidence", "low"),
        timestamp=utc_now_iso(),
        execution_time_ms=round((time.monotonic() - start) * 1000, 2),
        model=model,
        metadata={**metadata, **result.metadata},
    )


async def _handle_web_search(
    query: str, intent_result, metadata: dict, start: float
) -> CoreResponse:
    web_result = await web_agent.execute(query)

    if not web_result.success:
        metrics.record_error("web_agent")
        return await _handle_conversation(query, intent_result, metadata, start)

    if web_result.latency_ms:
        metrics.record_latency("web_agent", web_result.latency_ms)

    llm_result = await llm_agent.execute(query=query, context_data=web_result.content)

    if not llm_result.success:
        metrics.record_error("llm_agent")
        response_text = web_result.content
        model         = None
    else:
        response_text = llm_result.content
        model         = llm_result.metadata.get("model")
        metrics.record_model_call(model)
        if llm_result.latency_ms:
            metrics.record_latency("llm_agent", llm_result.latency_ms)

    metadata["web_sources"] = web_result.metadata.get("sources", [])
    await _store_memory(query, response_text, metadata)

    return CoreResponse(
        response=response_text,
        intent="web_search",
        agent="web_agent+llm_agent",
        confidence=intent_result.confidence,
        timestamp=utc_now_iso(),
        execution_time_ms=round((time.monotonic() - start) * 1000, 2),
        model=model,
        metadata={**metadata, **(llm_result.metadata if llm_result.success else {})},
    )


async def _handle_ha_action(
    query: str, intent_result, metadata: dict, start: float
) -> CoreResponse:
    result  = await ha_agent.execute(query)
    elapsed = round((time.monotonic() - start) * 1000, 2)

    if result.success:
        return CoreResponse(
            response=result.content,
            intent=intent_result.intent.value,
            agent="ha_agent",
            confidence=intent_result.confidence,
            timestamp=utc_now_iso(),
            execution_time_ms=elapsed,
            metadata=result.metadata,
        )
    return CoreResponse(
        response=f"Je n'ai pas pu exécuter cette action : {result.error}",
        intent=intent_result.intent.value,
        agent="ha_agent",
        confidence=intent_result.confidence,
        timestamp=utc_now_iso(),
        execution_time_ms=elapsed,
        error=result.error,
        metadata={},
    )


async def _handle_code(
    query: str, intent_result, metadata: dict, start: float
) -> CoreResponse:
    # FIX: imports re et unicodedata déplacés en tête de fichier
    path_match = re.search(r"(\S+\.py)", query)
    path       = path_match.group(1) if path_match else ""

    if not path:
        def _norm(t: str) -> str:
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

    result            = await code_agent.execute(query, path=path)
    execution_time_ms = round((time.monotonic() - start) * 1000, 2)

    if not result.success:
        metrics.record_error("code_agent")
        return CoreResponse(
            response=f"Je n'ai pas pu exécuter cette action : {result.error}",
            intent="code",
            agent="code_agent",
            confidence=intent_result.confidence,
            timestamp=utc_now_iso(),
            execution_time_ms=execution_time_ms,
            error=result.error,
            metadata={},
        )

    metrics.record_latency("code_agent", result.latency_ms or 0)
    return CoreResponse(
        response=result.content,
        intent="code",
        agent="code_agent",
        confidence=intent_result.confidence,
        timestamp=utc_now_iso(),
        execution_time_ms=execution_time_ms,
        metadata=result.metadata,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
