# modules/neron_core/app.py

# Néron Core v1.3.1 — Orchestrateur + Métriques + JSON Logging

"""
Pipeline :
Requête → IntentRouter → Agent(s) → [LLM synthèse] → Réponse

Nouveautés v1.3.1 :

- Métriques Prometheus : /metrics
- JSON logging structuré
- Registre dynamique d'agents
- Gestion d'erreurs réseau robuste
  """

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
from orchestrator.router import IntentRouter, Intent

# —————————————————————————

# Logging JSON global

# —————————————————————————

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger("neron_core")

# —————————————————————————

# Métriques Prometheus simples (Fix #7)

# —————————————————————————

class Metrics:
"""Compteurs en mémoire, exposés au format Prometheus text."""

```
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
    # On garde seulement les 1000 dernières mesures
    if len(self._latencies) > 1000:
        self._latencies = self._latencies[-1000:]

def export(self) -> str:
    lines = [
        "# HELP neron_intent_total Nombre de requêtes par intent",
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

    # Latence moyenne par agent
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
```

metrics = Metrics()

# —————————————————————————

# Instances globales

# —————————————————————————

llm_agent: LLMAgent = None
web_agent: WebAgent = None
router: IntentRouter = None

@asynccontextmanager
async def lifespan(app: FastAPI):
global llm_agent, web_agent, router

```
logger.info(json.dumps({"event": "startup", "version": "1.3.1"}))

llm_agent = LLMAgent()
web_agent = WebAgent()
router = IntentRouter(llm_agent=llm_agent)

logger.info(json.dumps({
    "event": "agents_ready",
    "agents": ["llm_agent", "web_agent"]
}))

yield

logger.info(json.dumps({"event": "shutdown"}))
```

# —————————————————————————

# FastAPI

# —————————————————————————

app = FastAPI(
title="Néron Core",
description="Orchestrateur central — v1.3.1",
version="1.3.1",
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

# —————————————————————————

# Endpoints

# —————————————————————————

@app.get("/")
def root():
return {
"service": "Néron Core",
"version": "1.3.1",
"status": "active",
"agents": ["llm_agent", "web_agent"],
"next": "ha_agent (v1.4.0)"
}

@app.get("/health")
def health():
return {"status": "healthy", "version": "1.3.1"}

@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
"""Endpoint Prometheus — compatible Prometheus scraper."""
return PlainTextResponse(metrics.export(), media_type="text/plain")

@app.post("/input/text", response_model=CoreResponse)
async def text_input(input_data: TextInput):
query = input_data.text.strip()
start = time.monotonic()

```
logger.info(json.dumps({
    "event": "request_received",
    "query": query[:80]
}))

# --- Routage ---
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

# --- Dispatch via registre dynamique (Fix #2) ---
if intent_result.intent == Intent.WEB_SEARCH:
    core_response = await _handle_web_search(query, intent_result, metadata)

elif intent_result.intent == Intent.HA_ACTION:
    # Réservé v1.4.0
    logger.info(json.dumps({"event": "ha_action_fallback"}))
    core_response = await _handle_conversation(
        "Je n'ai pas encore accès à Home Assistant. " + query,
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
```

# —————————————————————————

# Handlers

# —————————————————————————

async def _handle_conversation(query: str, metadata: dict) -> CoreResponse:
result = await llm_agent.execute(query)

```
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
```

async def _handle_web_search(query: str, intent_result, metadata: dict) -> CoreResponse:
# Recherche web
web_result = await web_agent.execute(query)

```
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

# Synthèse LLM
llm_result = await llm_agent.execute(
    query=query,
    context_data=web_result.content
)

if not llm_result.success:
    metrics.record_error("llm_agent")
    response_text = web_result.content  # fallback résultats bruts
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
```

async def _store_memory(query: str, response: str, metadata: dict):
memory_url = os.getenv("NERON_MEMORY_URL", "http://neron_memory:8002")
try:
async with httpx.AsyncClient(timeout=5.0) as client:
await client.post(
f"{memory_url}/store",
json={"input": query, "response": response, "metadata": metadata}
)
except Exception as e:
logger.warning(json.dumps({
"event": "memory_store_failed",
"error": str(e)
}))

# —————————————————————————

# Point d'entrée

# —————————————————————————

if **name** == "**main**":
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)
