# api/server.py
from fastapi import FastAPI
from core.manager import LLMManager
from core.models import LLMRequest

app = FastAPI()
manager = LLMManager()

@app.post("/chat")
async def chat(req: LLMRequest):
    return await manager.generate(req)
