# server/webapi.py
# Neron WebAPI v1.1.0
#
# Facade externe légère — délègue TOUT à core/app.py via HTTP.
# Aucun import interne de core. Aucune logique métier ici.

from __future__ import annotations

import json
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.agents.base_agent import get_logger
from core.config import settings

logger = get_logger("webapi")
app = FastAPI(title="Neron WebAPI", version="1.1.0")

# URL de base vers core/app.py — résolu depuis settings
def _core_url(path: str) -> str:
    return f"http://{settings.SERVER_HOST}:{settings.SERVER_PORT}{path}"

def _core_headers() -> dict:
    return {"X-API-Key": settings.API_KEY} if settings.API_KEY else {}


# ── Mémoire ───────────────────────────────────────────────────────────────────

@app.get("/memory")
async def get_memory(limit: int = 5):
    """Proxy vers GET /memory de core."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                _core_url("/memory"),
                params={"limit": limit},
                headers=_core_headers(),
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Erreur get_memory: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Commande texte ────────────────────────────────────────────────────────────

@app.post("/command")
async def run_command(request: Request):
    """Proxy vers POST /input/text de core."""
    data = await request.json()
    cmd = data.get("cmd", "").strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="Commande vide")
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(
                _core_url("/input/text"),
                json={"text": cmd},
                headers=_core_headers(),
            )
            resp.raise_for_status()
            body = resp.json()
            return {"response": body.get("response", "❌ Pas de réponse")}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Erreur run_command: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Streaming SSE ─────────────────────────────────────────────────────────────

@app.post("/stream")
async def stream_command(request: Request):
    """Proxy SSE vers POST /input/stream de core, avec throttle 500 ms."""
    data = await request.json()
    text = data.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texte vide")

    async def event_generator():
        accumulated = ""
        last_edit   = ""
        last_update = time.time()
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    _core_url("/input/stream"),
                    json={"text": text},
                    headers=_core_headers(),
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            payload = json.loads(line[6:])
                            token   = payload.get("token", "")
                            done    = payload.get("done", False)
                            accumulated += token
                            now = time.time()
                            if (now - last_update > 0.5 or done) and accumulated != last_edit:
                                yield f"data: {json.dumps({'token': accumulated, 'done': done})}\n\n"
                                last_edit   = accumulated
                                last_update = now
                            if done:
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error("Erreur stream_command: %s", e)
            yield f"data: {json.dumps({'token': '', 'done': True, 'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Twilio / appel vocal ──────────────────────────────────────────────────────

@app.post("/call")
async def make_call(request: Request):
    """Déclenche un appel Twilio avec le message fourni."""
    data    = await request.json()
    message = data.get("message", "Message Néron")
    try:
        from core.tools.twilio_tool import call as twilio_call
        twilio_call(message)
        return {"status": "ok"}
    except Exception as e:
        logger.error("Erreur Twilio call: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
