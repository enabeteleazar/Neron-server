from fastapi import FastAPI, HTTPException

from neron_llm.core.manager import LLMManager
from neron_llm.core.models import LLMRequest

app = FastAPI(title="Néron LLM")
manager = LLMManager()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: LLMRequest):
    try:
        if req.mode == "parallel":
            return await manager.generate_parallel(req)
        elif req.mode == "race":
            return await manager.generate_race(req)
        else:
            return await manager.generate(req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))