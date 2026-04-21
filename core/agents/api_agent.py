from __future__ import annotations

import asyncio
import json
import logging
import threading
import traceback
from typing import Optional, AsyncGenerator

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from serverVNext.serverVNext.core.agents.base_agent import BaseAgent, AgentResult
from serverVNext.serverVNext.core.config import settings

logger = logging.getLogger("agent.api_agent")

# ── Pydantic Models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    success: bool

class TextInputRequest(BaseModel):
    text: str
    mode: Optional[str] = None
    context: Optional[str] = None

class TextInputResponse(BaseModel):
    response: str
    success: bool
    mode: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    context: Optional[str] = None

# ── Agents partagés (injectés au démarrage) ───────────────────────────────────

_llm_agent = None
_intent_router = None

def init_agents() -> None:
    """Initialise LLMAgent + IntentRouter dans le process de l'APIAgent."""
    global _llm_agent, _intent_router
    from serverVNext.serverVNext.core.agents.llm_agent import LLMAgent
    from serverVNext.serverVNext.core.orchestrator.intent_router import IntentRouter

    _llm_agent     = LLMAgent()
    _intent_router = IntentRouter(llm_agent=_llm_agent)

# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="Neron AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth helper ───────────────────────────────────────────────────────────────

def _check_api_key(x_api_key: str | None) -> None:
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Neron AI API", "version": settings.VERSION}


@app.get("/status")
async def status():
    llm_ok = False
    if _llm_agent is not None:
        try:
            llm_ok = await _llm_agent.check_connection()
        except Exception:
            pass
    return {
        "status": "online",
        "service": "neron_api",
        "version": settings.VERSION,
        "llm_ready": llm_ok,
        "model": settings.OLLAMA_MODEL,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(default=None),
):
    _check_api_key(x_api_key)
    if _llm_agent is None:
        return ChatResponse(response="❌ LLMAgent non initialisé", success=False)

    result = await _llm_agent.execute(
        query=request.message,
        context_data=request.context,
    )
    return ChatResponse(
        response=result.content if result.success else f"❌ {result.content}",
        success=result.success,
    )


@app.post("/input/text", response_model=TextInputResponse)
async def input_text(
    request: TextInputRequest,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Point d'entrée principal — bot Telegram et autres agents.

    Modes :
    - pipeline  : routage Intent puis LLM
    - plan      : prompt de planification
    - autopilot : prompt autonome étendu
    - standard  : LLM direct
    - default   : LLM direct
    """
    try:
        _check_api_key(x_api_key)

        text = (request.text or "").strip()
        mode = (request.mode or "default").strip()

        if not text:
            return TextInputResponse(
                response="❌ Aucun texte fourni.",
                success=False,
                mode=mode,
            )

        if _llm_agent is None:
            return TextInputResponse(
                response="❌ LLMAgent non disponible — Ollama est-il démarré ?",
                success=False,
                mode=mode,
            )

        # ── Routing par mode ──────────────────────────────────────────────────
        result = None
        intent_str = None
        confidence_value = None

        try:
            if mode == "pipeline" and _intent_router is not None:
                intent_result = await _intent_router.route(text)
                result = await _llm_agent.execute(query=text, context_data=request.context)
                intent_str = intent_result.intent.value
                confidence_value = intent_result.confidence

            elif mode == "plan":
                query = f"Crée un plan détaillé étape par étape pour accomplir cette tâche : {text}"
                result = await _llm_agent.execute(query=query, context_data=request.context)

            elif mode == "autopilot":
                query = (
                    f"Tu es en mode autonome. Analyse cette tâche, décompose-la "
                    f"et donne le résultat final : {text}"
                )
                result = await _llm_agent.execute(query=query, context_data=request.context)

            else:
                # Default mode
                result = await _llm_agent.execute(query=text, context_data=request.context)
        
        except Exception as e:
            return TextInputResponse(
                response=f"❌ Erreur LLM: {str(e)}",
                success=False,
                mode=mode,
            )

        if result is None:
            return TextInputResponse(
                response="❌ Pas de résultat du LLM",
                success=False,
                mode=mode,
            )

        return TextInputResponse(
            response=result.content if result.success else f"❌ {result.error or 'Erreur inconnue'}",
            success=result.success,
            mode=mode,
            intent=intent_str,
            confidence=confidence_value,
            context=request.context,
        )
    
    except Exception as e:
        # Catch-all pour toute exception non prévue
        import traceback
        logger.error("Exception dans /input/text: %s", traceback.format_exc())
        return TextInputResponse(
            response=f"❌ Erreur serveur: {str(e)}",
            success=False,
            mode="default",
        )


async def _stream_response(
    text: str,
    mode: str,
    context: Optional[str],
) -> AsyncGenerator[str, None]:
    """Générateur pour streamer la réponse par chunks."""
    
    # Validation basique
    text = (text or "").strip()
    mode = (mode or "default").strip()

    if not text:
        yield json.dumps({"type": "error", "message": "❌ Aucun texte fourni."}) + "\n"
        return

    if _llm_agent is None:
        yield json.dumps({"type": "error", "message": "❌ LLMAgent non disponible"}) + "\n"
        return

    try:
        # Préparer la requête selon le mode
        if mode == "plan":
            query = f"Crée un plan détaillé étape par étape pour accomplir cette tâche : {text}"
        elif mode == "autopilot":
            query = f"Tu es en mode autonome. Analyse cette tâche, décompose-la et donne le résultat final : {text}"
        elif mode == "pipeline" and _intent_router is not None:
            # Mode pipeline: route intent en premier
            try:
                intent_result = await _intent_router.route(text)
                yield json.dumps({
                    "type": "metadata",
                    "intent": intent_result.intent.value,
                    "confidence": intent_result.confidence,
                }) + "\n"
            except Exception as e:
                yield json.dumps({"type": "error", "message": f"❌ Erreur pipeline: {str(e)}"}) + "\n"
                return
            query = text
        else:
            query = text

        # Exécuter la requête
        result = await _llm_agent.execute(query=query, context_data=context)

        # Streamer la réponse par caractères (ou par chunks si disponible)
        if result.success:
            content = result.content
            # Streamer par chunks de 20 caractères pour créer l'effet de streaming
            chunk_size = 20
            for i in range(0, len(content), chunk_size):
                chunk = content[i : i + chunk_size]
                yield json.dumps({"type": "chunk", "data": chunk}) + "\n"
                await asyncio.sleep(0.01)  # Petit délai pour le streaming
            yield json.dumps({"type": "complete", "success": True}) + "\n"
        else:
            yield json.dumps({"type": "error", "message": f"❌ {result.content}"}) + "\n"

    except Exception as e:
        yield json.dumps({"type": "error", "message": f"❌ Exception: {str(e)}"}) + "\n"


@app.post("/input/stream")
async def input_stream(
    request: TextInputRequest,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Endpoint de streaming pour les réponses texte.
    
    Retourne un stream NDJSON (newline-delimited JSON):
    - {"type": "metadata", "intent": "...", "confidence": ...}
    - {"type": "chunk", "data": "..."}
    - {"type": "complete", "success": true}
    - {"type": "error", "message": "..."}
    
    Modes :
    - pipeline  : routage Intent puis LLM
    - plan      : prompt de planification
    - autopilot : prompt autonome étendu
    - default   : LLM direct
    """
    _check_api_key(x_api_key)

    return StreamingResponse(
        _stream_response(
            text=request.text,
            mode=request.mode or "default",
            context=request.context,
        ),
        media_type="application/x-ndjson",
    )


# ── Agent ────────────────────────────────────────────────────────────────────

class APIAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="api_agent")
        self.logger.info(
            "APIAgent init — host: %s | port: %d",
            settings.SERVER_HOST,
            settings.SERVER_PORT,
        )

    async def execute(self, query: str, context_data=None, **kwargs) -> AgentResult:
        return AgentResult(
            success=False,
            content="API agent does not process queries directly",
            source="api_agent",
        )

    async def run(self) -> None:
        """Initialise les agents puis démarre le serveur FastAPI."""
        init_agents()
        self.logger.info("LLMAgent + IntentRouter initialisés dans APIAgent")

        thread = threading.Thread(
            target=lambda: uvicorn.run(
                app,
                host=settings.SERVER_HOST,
                port=settings.SERVER_PORT,
                log_level="info",
            ),
            daemon=True,
        )
        thread.start()
        self.logger.info(
            "Serveur FastAPI démarré sur http://%s:%d",
            settings.SERVER_HOST,
            settings.SERVER_PORT,
        )
        await asyncio.Event().wait()