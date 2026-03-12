# core/app.py
# Neron Core v2.1.0

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, File, HTTPException, UploadFile, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from agents.llm_agent import LLMAgent
from agents.web_agent import WebAgent
from agents.stt_agent import STTAgent, load_model as stt_load_model
# from agents.tts_agent import TTSAgent, load_engine as tts_load_engine  # TTS désactivé
from agents.memory_agent import MemoryAgent, init_db as memory_init_db
from agents.telegram_agent import start_bot, stop_bot, set_agents, send_notification
from agents.watchdog_agent import setup as watchdog_setup, start_watchdog, stop_watchdog, start_watchdog_bot, stop_watchdog_bot
from agents.ha_agent import HAAgent
from agents.base_agent import get_logger
from orchestrator.intent_router import IntentRouter, Intent
from neron_time.time_provider import TimeProvider
from config import settings

logging.basicConfig(level=settings.LOG_LEVEL)

# FileHandler — écriture logs dans data/logs/
_log_file = settings.LOGS_DIR / settings.LOG_NERON
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
_file_handler = logging.FileHandler(_log_file)
_file_handler.setLevel(settings.LOG_LEVEL)
_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(_file_handler)
logger = get_logger("neron_core")

VERSION = "2.1.0"
_startup_time: float = 0.0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Metrics:
    def __init__(self):
        self._intent_counts: dict = {}
        self._agent_errors: dict = {}
        self._latencies: dict = {}
        self._requests_total: int = 0
        self._requests_in_flight: int = 0
        self._execution_times: list = []
        self._model_calls: dict = {}

    def record_request_start(self):
        self._requests_total += 1
        self._requests_in_flight += 1

    def record_request_end(self, execution_time_ms: float):
        self._requests_in_flight = max(0, self._requests_in_flight - 1)
        self._execution_times.append(execution_time_ms)
        if len(self._execution_times) > 1000:
            self._execution_times = self._execution_times[-1000:]

    def record_intent(self, intent: str):
        self._intent_counts[intent] = self._intent_counts.get(intent, 0) + 1

    def record_error(self, agent: str):
        self._agent_errors[agent] = self._agent_errors.get(agent, 0) + 1

    def record_latency(self, agent: str, latency_ms: float):
        self._latencies.setdefault(agent, []).append(latency_ms)
        if len(self._latencies[agent]) > 1000:
            self._latencies[agent] = self._latencies[agent][-1000:]

    def record_model_call(self, model: str):
        if model:
            self._model_calls[model] = self._model_calls.get(model, 0) + 1

    def export(self) -> str:
        lines = []
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
            avg_exec = round(sum(self._execution_times) / len(self._execution_times), 2)
            lines += [
                "# HELP neron_execution_time_avg_ms Temps moyen orchestration (ms)",
                "# TYPE neron_execution_time_avg_ms gauge",
                f"neron_execution_time_avg_ms {avg_exec}",
            ]
        lines += ["# HELP neron_intent_total Requetes par intent", "# TYPE neron_intent_total counter"]
        for intent, count in self._intent_counts.items():
            lines.append(f'neron_intent_total{{intent="{intent}"}} {count}')
        lines += ["# HELP neron_agent_errors_total Erreurs par agent", "# TYPE neron_agent_errors_total counter"]
        for agent, count in self._agent_errors.items():
            lines.append(f'neron_agent_errors_total{{agent="{agent}"}} {count}')
        lines += ["# HELP neron_agent_latency_avg_ms Latence moyenne par agent (ms)", "# TYPE neron_agent_latency_avg_ms gauge"]
        for agent, values in self._latencies.items():
            avg = round(sum(values) / len(values), 2)
            lines.append(f'neron_agent_latency_avg_ms{{agent="{agent}"}} {avg}')
        lines += ["# HELP neron_llm_calls_by_model Appels LLM par modele", "# TYPE neron_llm_calls_by_model counter"]
        for model, count in self._model_calls.items():
            lines.append(f'neron_llm_calls_by_model{{model="{model}"}} {count}')
        return "\n".join(lines) + "\n"


metrics = Metrics()

llm_agent: LLMAgent = None
memory_agent: MemoryAgent = None
web_agent: WebAgent = None
stt_agent: STTAgent = None
tts_agent = None  # TTS désactivé
ha_agent: HAAgent = None
router: IntentRouter = None
time_provider: TimeProvider = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_agent, web_agent, stt_agent, tts_agent, ha_agent, router, time_provider, _startup_time, memory_agent

    _startup_time = time.monotonic()
    logger.info(json.dumps({"event": "startup", "version": VERSION}))

    llm_agent = LLMAgent()
    web_agent = WebAgent()
    memory_init_db()
    memory_agent = MemoryAgent()
    stt_load_model()
    stt_agent = STTAgent()

    # Home Assistant — instanciation + chargement des entités
    ha_agent = HAAgent()
    await ha_agent.on_start()

    # tts_load_engine()  # TTS désactivé
    # tts_agent = TTSAgent()  # TTS désactivé

    router = IntentRouter(llm_agent=llm_agent)
    time_provider = TimeProvider()

    logger.info(json.dumps({"event": "agents_ready"}))

    set_agents({"llm": llm_agent, "stt": stt_agent, "tts": tts_agent, "memory": memory_agent})

    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN not in ("", "votre_token_ici"):
        await start_bot()
    else:
        logger.warning("Telegram desactive -- TELEGRAM_BOT_TOKEN non configure")

    if settings.WATCHDOG_ENABLED:
        watchdog_setup(
            agents={"llm": llm_agent, "stt": stt_agent, "tts": tts_agent},
            notify_fn=send_notification
        )
        await start_watchdog()
        await start_watchdog_bot()

    yield

    if settings.WATCHDOG_ENABLED:
        await stop_watchdog_bot()
        await stop_watchdog()
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN not in ("", "votre_token_ici"):
        await stop_bot()
    logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(
    title="Neron Core",
    description="Orchestrateur central - v" + VERSION,
    version=VERSION,
    lifespan=lifespan
)


class TextInput(BaseModel):
    text: str


class CoreResponse(BaseModel):
    response: str
    intent: str
    agent: str
    confidence: str
    timestamp: str
    execution_time_ms: float
    model: Optional[str] = None
    error: Optional[str] = None
    transcription: Optional[str] = None
    metadata: dict = {}


@app.get("/")
def root():
    return {"service": "Neron Core", "version": VERSION, "status": "active"}


@app.get("/health")
def health():
    return {"status": "healthy", "version": VERSION}


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return PlainTextResponse(metrics.export(), media_type="text/plain")


API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if not settings.API_KEY or settings.API_KEY == "changez_moi":
        return
    if api_key is None:
        raise HTTPException(status_code=401, detail="API Key manquante")
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="API Key invalide")


@app.post("/input/text", response_model=CoreResponse)
async def text_input(input_data: TextInput, _: None = Depends(verify_api_key)):
    query = input_data.text.strip()
    start = time.monotonic()
    metrics.record_request_start()

    logger.info(json.dumps({"event": "request_received", "query": query[:80]}))

    intent_result = await router.route(query)
    metrics.record_intent(intent_result.intent.value)

    metadata = {"intent": intent_result.intent.value, "confidence": intent_result.confidence}

    try:
        if intent_result.intent == Intent.TIME_QUERY:
            core_response = _handle_time_query(intent_result, metadata, start, query)
        elif intent_result.intent == Intent.WEB_SEARCH:
            core_response = await _handle_web_search(query, intent_result, metadata, start)
        elif intent_result.intent == Intent.HA_ACTION:
            core_response = await _handle_ha_action(query, intent_result, metadata, start)
        else:
            core_response = await _handle_conversation(query, intent_result, metadata, start)
    finally:
        elapsed = round((time.monotonic() - start) * 1000, 2)
        metrics.record_request_end(elapsed)

    return core_response


@app.post("/input/stream")
async def text_input_stream(input_data: TextInput, _: None = Depends(verify_api_key)):
    from fastapi.responses import StreamingResponse

    query = input_data.text.strip()

    async def generate():
        intent_result = await router.route(query)
        if intent_result.intent == Intent.TIME_QUERY:
            response = _handle_time_query(intent_result, {}, 0, query).response
            yield f"data: {json.dumps({'token': response, 'done': True})}\n\n"
            return

        memory_context = await _get_memory_context(query)
        full_response = ""
        async for token in llm_agent.stream(query, context_data=memory_context or None):
            full_response += token
            yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"

        yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
        await _store_memory(query, full_response, {"intent": intent_result.intent.value})

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/input/audio", response_model=CoreResponse)
async def audio_input(file: UploadFile = File(...)):
    start = time.monotonic()
    metrics.record_request_start()

    try:
        audio_bytes = await file.read()
        result = await stt_agent.transcribe(audio_bytes, file.filename)

        if not result.success:
            metrics.record_error("stt_agent")
            raise HTTPException(503, f"STT indisponible : {result.error}")

        if result.latency_ms:
            metrics.record_latency("stt_agent", result.latency_ms)

        transcription = result.content
        input_data = TextInput(text=transcription)
        core_response = await text_input(input_data)
        core_response.transcription = transcription
        core_response.metadata["stt"] = {
            "language": result.metadata.get("language"),
            "stt_latency_ms": result.latency_ms
        }
        return core_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur pipeline audio : {str(e)}")
    finally:
        elapsed = round((time.monotonic() - start) * 1000, 2)
        metrics.record_request_end(elapsed)


@app.post("/input/voice")
async def voice_input(file: UploadFile = File(...)):
    from fastapi.responses import Response as FastAPIResponse

    start = time.monotonic()
    metrics.record_request_start()

    try:
        audio_bytes = await file.read()
        stt_result = await stt_agent.transcribe(audio_bytes, file.filename)

        if not stt_result.success:
            metrics.record_error("stt_agent")
            raise HTTPException(503, f"STT indisponible : {stt_result.error}")

        if stt_result.latency_ms:
            metrics.record_latency("stt_agent", stt_result.latency_ms)

        transcription = stt_result.content
        if not transcription:
            raise HTTPException(400, "Transcription vide")

        input_data = TextInput(text=transcription)
        core_response = await text_input(input_data)

        tts_result = await tts_agent.synthesize(core_response.response)

        if not tts_result.success:
            metrics.record_error("tts_agent")
            return core_response

        if tts_result.latency_ms:
            metrics.record_latency("tts_agent", tts_result.latency_ms)

        execution_time_ms = round((time.monotonic() - start) * 1000, 2)
        return FastAPIResponse(
            content=tts_result.metadata["audio_bytes"],
            media_type="audio/wav",
            headers={
                "X-Transcription": transcription[:200],
                "X-Response-Text": core_response.response[:200],
                "X-Intent": core_response.intent,
                "X-Execution-Time-Ms": str(execution_time_ms),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur pipeline vocal : {str(e)}")
    finally:
        elapsed = round((time.monotonic() - start) * 1000, 2)
        metrics.record_request_end(elapsed)


def _handle_time_query(intent_result, metadata: dict, start: float, query: str = "") -> CoreResponse:
    q = query.lower()
    heure_keys = ["heure", "time", "il est", "quelle heure"]
    date_keys = ["date", "jour", "quel jour", "quel mois", "quelle date", "on est"]
    want_heure = any(k in q for k in heure_keys)
    want_date = any(k in q for k in date_keys)
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
    execution_time_ms = round((time.monotonic() - start) * 1000, 2)
    return CoreResponse(
        response=response, intent="time_query", agent="time_provider",
        confidence=intent_result.confidence, timestamp=utc_now_iso(),
        execution_time_ms=execution_time_ms, model=None, error=None,
        metadata={**metadata, "iso": time_provider.iso(), "timestamp": time_provider.timestamp()}
    )


async def _get_memory_context(query: str) -> str:
    context_parts = []
    try:
        recent = memory_agent.retrieve(limit=3)
        if recent:
            history = []
            for entry in reversed(recent):
                history.append(f"Utilisateur: {entry['input']}")
                history.append(f"Neron: {entry['response'][:80]}")
            context_parts.append("Historique recent:\n" + "\n".join(history))
        relevant = memory_agent.search(query, limit=3)
        if relevant:
            facts = [f"- Q: {entry['input']} -> R: {entry['response'][:100]}" for entry in relevant]
            context_parts.append("Memoire pertinente:\n" + "\n".join(facts))
    except Exception as e:
        logger.warning(json.dumps({"event": "memory_context_failed", "error": str(e)}))
    return "\n\n".join(context_parts)


async def _handle_conversation(query: str, intent_result, metadata: dict, start: float) -> CoreResponse:
    memory_context = await _get_memory_context(query)
    result = await llm_agent.execute(query, context_data=memory_context if memory_context else None)

    if not result.success:
        metrics.record_error("llm_agent")
        raise HTTPException(503, f"LLM indisponible : {result.error}")

    if result.latency_ms:
        metrics.record_latency("llm_agent", result.latency_ms)

    model = result.metadata.get("model")
    metrics.record_model_call(model)
    execution_time_ms = round((time.monotonic() - start) * 1000, 2)
    await _store_memory(query, result.content, metadata)

    return CoreResponse(
        response=result.content, intent=metadata.get("intent", "conversation"),
        agent="llm_agent", confidence=metadata.get("confidence", "low"),
        timestamp=utc_now_iso(), execution_time_ms=execution_time_ms,
        model=model, error=None, metadata={**metadata, **result.metadata}
    )


async def _handle_web_search(query: str, intent_result, metadata: dict, start: float) -> CoreResponse:
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
        model = None
    else:
        response_text = llm_result.content
        model = llm_result.metadata.get("model")
        metrics.record_model_call(model)
        if llm_result.latency_ms:
            metrics.record_latency("llm_agent", llm_result.latency_ms)

    execution_time_ms = round((time.monotonic() - start) * 1000, 2)
    metadata["web_sources"] = web_result.metadata.get("sources", [])
    await _store_memory(query, response_text, metadata)

    return CoreResponse(
        response=response_text, intent="web_search", agent="web_agent+llm_agent",
        confidence=intent_result.confidence, timestamp=utc_now_iso(),
        execution_time_ms=execution_time_ms, model=model, error=None,
        metadata={**metadata, **(llm_result.metadata if llm_result.success else {})}
    )


async def _handle_ha_action(query: str, intent_result, metadata: dict, start: float) -> CoreResponse:
    """Pipeline Home Assistant : parse action → appel REST HA → réponse"""
    result = await ha_agent.execute(query)
    elapsed = round((time.monotonic() - start) * 1000, 2)

    if result.success:
        return CoreResponse(
            response=result.content,
            intent=intent_result.intent.value,
            agent="ha_agent",
            confidence=intent_result.confidence,
            timestamp=utc_now_iso(),
            execution_time_ms=elapsed,
            metadata=result.metadata
        )
    else:
        fallback = f"Je n'ai pas pu exécuter cette action : {result.error}"
        return CoreResponse(
            response=fallback,
            intent=intent_result.intent.value,
            agent="ha_agent",
            confidence=intent_result.confidence,
            timestamp=utc_now_iso(),
            execution_time_ms=elapsed,
            error=result.error,
            metadata={}
        )


async def _store_memory(query: str, response: str, metadata: dict):
    try:
        memory_agent.store(query, response, metadata)
    except Exception as e:
        logger.warning(json.dumps({"event": "memory_store_failed", "error": str(e)}))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
