# modules/neron_core/app.py
# Neron Core v1.3.3 - Orchestrateur + TimeProvider

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from agents.llm_agent import LLMAgent
from agents.web_agent import WebAgent
from agents.base_agent import get_logger
from orchestrator.intent_router import IntentRouter, Intent
from neron_time.time_provider import TimeProvider

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger("neron_core")


class Metrics:
    def __init__(self):
        self._intent_counts: dict = {}
        self._agent_errors: dict = {}
        self._latencies: list = []

    def record_intent(self, intent: str):
        self._intent_counts[intent] = self._intent_counts.get(intent, 0) + 1

    def record_error(self, agent: str):
        self._agent_errors[agent] = self._agent_errors.get(agent, 0) + 1

    def record_latency(self, agent: str, latency_ms: float):
        self._latencies.append({"agent": agent, "latency_ms": latency_ms})
        if len(self._latencies) > 1000:
            self._latencies = self._latencies[-1000:]

    def export(self) -> str:
        lines = [
            "# HELP neron_intent_total Nombre de requetes par intent",
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
        agent_latencies: dict = {}
        for entry in self._latencies:
            a = entry["agent"]
            agent_latencies.setdefault(a, []).append(entry["latency_ms"])
        lines += [
            "# HELP neron_agent_latency_avg_ms Latence moyenne par agent (ms)",
            "# TYPE neron_agent_latency_avg_ms gauge",
        ]
        for agent, values in agent_latencies.items():
            avg = sum(values) / len(values)
            lines.append(f'neron_agent_latency_avg_ms{{agent="{agent}"}} {avg:.2f}')
        return "\n".join(lines) + "\n"


metrics = Metrics()

llm_agent: LLMAgent = None
web_agent: WebAgent = None
router: IntentRouter = None
time_provider: TimeProvider = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_agent, web_agent, router, time_provider

    logger.info(json.dumps({"event": "startup", "version": "1.3.3"}))
    llm_agent = LLMAgent()
    web_agent = WebAgent()
    router = IntentRouter(llm_agent=llm_agent)
    time_provider = TimeProvider()
    logger.info(json.dumps({
        "event": "agents_ready",
        "agents": ["llm_agent", "web_agent", "time_provider"]
    }))
    yield
    logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(
    title="Neron Core",
    description="Orchestrateur central - v1.3.3",
    version="1.3.3",
    lifespan=lifespan
)


class TextInput(BaseModel):
    text: str


class CoreResponse(BaseModel):
    response: str
    intent: str
    confidence: str
    transcription: Optional[str] = None
    metadata: dict = {}


@app.get("/")
def root():
    return {
        "service": "Neron Core",
        "version": "1.3.3",
        "status": "active",
        "agents": ["llm_agent", "web_agent", "time_provider"],
        "next": "ha_agent (v1.4.0)"
    }


@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.3.3"}


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return PlainTextResponse(metrics.export(), media_type="text/plain")


@app.post("/input/text", response_model=CoreResponse)
async def text_input(input_data: TextInput):
    query = input_data.text.strip()
    start = time.monotonic()

    logger.info(json.dumps({"event": "request_received", "query": query[:80]}))

    intent_result = await router.route(query)
    metrics.record_intent(intent_result.intent.value)

    logger.info(json.dumps({
        "event": "intent_resolved",
        "intent": intent_result.intent.value,
        "confidence": intent_result.confidence
    }))

    metadata = {
        "intent": intent_result.intent.value,
        "confidence": intent_result.confidence,
    }

    if intent_result.intent == Intent.TIME_QUERY:
        core_response = _handle_time_query(intent_result, metadata)
    elif intent_result.intent == Intent.WEB_SEARCH:
        core_response = await _handle_web_search(query, intent_result, metadata)
    elif intent_result.intent == Intent.HA_ACTION:
        logger.info(json.dumps({"event": "ha_action_fallback"}))
        core_response = await _handle_conversation(
            "Je n'ai pas encore acces a Home Assistant. " + query,
            metadata
        )
    else:
        core_response = await _handle_conversation(query, metadata)

    elapsed = round((time.monotonic() - start) * 1000, 2)
    logger.info(json.dumps({
        "event": "request_completed",
        "intent": intent_result.intent.value,
        "total_latency_ms": elapsed
    }))

    return core_response


def _handle_time_query(intent_result, metadata: dict) -> CoreResponse:
    response = (
        "Il est " + time_provider.human() + "."
    )
    logger.info(json.dumps({"event": "time_query_handled", "response": response}))
    return CoreResponse(
        response=response,
        intent="time_query",
        confidence=intent_result.confidence,
        metadata={
            **metadata,
            "iso": time_provider.iso(),
            "timestamp": time_provider.timestamp()
        }
    )


async def _handle_conversation(query: str, metadata: dict) -> CoreResponse:
    result = await llm_agent.execute(query)

    if not result.success:
        metrics.record_error("llm_agent")
        raise HTTPException(503, f"LLM indisponible : {result.error}")

    if result.latency_ms:
        metrics.record_latency("llm_agent", result.latency_ms)

    await _store_memory(query, result.content, metadata)

    return CoreResponse(
        response=result.content,
        intent=metadata.get("intent", "conversation"),
        confidence=metadata.get("confidence", "low"),
        metadata={**metadata, **result.metadata}
    )


async def _handle_web_search(query: str, intent_result, metadata: dict) -> CoreResponse:
    web_result = await web_agent.execute(query)

    if not web_result.success:
        metrics.record_error("web_agent")
        logger.warning(json.dumps({
            "event": "web_agent_failed",
            "error": web_result.error,
            "fallback": "conversation"
        }))
        return await _handle_conversation(query, metadata)

    if web_result.latency_ms:
        metrics.record_latency("web_agent", web_result.latency_ms)

    llm_result = await llm_agent.execute(
        query=query,
        context_data=web_result.content
    )

    if not llm_result.success:
        metrics.record_error("llm_agent")
        response_text = web_result.content
    else:
        response_text = llm_result.content
        if llm_result.latency_ms:
            metrics.record_latency("llm_agent", llm_result.latency_ms)

    metadata["web_sources"] = web_result.metadata.get("sources", [])
    metadata["web_results_count"] = web_result.metadata.get("total_results", 0)

    await _store_memory(query, response_text, metadata)

    return CoreResponse(
        response=response_text,
        intent="web_search",
        confidence=intent_result.confidence,
        metadata={**metadata, **(llm_result.metadata if llm_result.success else {})}
    )


async def _store_memory(query: str, response: str, metadata: dict):
    memory_url = os.getenv("NERON_MEMORY_URL", "http://neron_memory:8002")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{memory_url}/store",
                json={"input": query, "response": response, "metadata": metadata}
            )
    except Exception as e:
        logger.warning(json.dumps({"event": "memory_store_failed", "error": str(e)}))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
