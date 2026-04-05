# server/webapi.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio
import json
import time
import httpx
from core.agents.telegram_agent import _agents, _normalize, _post_text
from core.agents.base_agent import get_logger
from core.tools.twilio_tool import call as twilio_call

logger = get_logger("webapi")
app = FastAPI()

# ── Mémoire ──────────────────────────────────────────────
@app.get("/memory")
async def get_memory(limit: int = 5):
    mem_agent = _agents.get("memory")
    if not mem_agent:
        raise HTTPException(status_code=404, detail="Agent mémoire non disponible")
    entries = mem_agent.retrieve(limit=limit)
    return {"entries": entries}

# ── Commandes / exécution ───────────────────────────────
@app.post("/command")
async def run_command(request: Request):
    data = await request.json()
    cmd = data.get("cmd", "")
    if not cmd:
        raise HTTPException(status_code=400, detail="Commande vide")
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await _post_text(client, cmd)
            return {"response": resp.get("response", "❌ Pas de réponse")}
    except Exception as e:
        logger.error("Erreur run_command: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# ── Streaming texte (comme Telegram /input/stream) ─────
@app.post("/stream")
async def stream_command(request: Request):
    data = await request.json()
    text = data.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Texte vide")

    async def event_generator():
        accumulated = ""
        last_edit = ""
        last_update = time.time()
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/input/stream",
                json={"text": text},
                headers={"X-API-Key": settings.API_KEY},
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data_line = json.loads(line[6:])
                        token = data_line.get("token", "")
                        done = data_line.get("done", False)
                        accumulated += token
                        now = time.time()
                        if (now - last_update > 0.5 or done) and accumulated != last_edit:
                            yield f"data: {json.dumps({'token': accumulated, 'done': done})}\n\n"
                            last_edit = accumulated
                            last_update = now
                        if done:
                            break
                    except json.JSONDecodeError:
                        continue
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ── Twilio / notifications ─────────────────────────────
@app.post("/call")
async def make_call(request: Request):
    data = await request.json()
    message = data.get("message", "Message Néron")
    try:
        twilio_call(message)
        return {"status": "ok"}
    except Exception as e:
        logger.error("Erreur Twilio call: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
