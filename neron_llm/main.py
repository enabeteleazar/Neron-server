from fastapi import FastAPI
from neron_llm.core.manager import LLMManager
from neron_llm.core.models import LLMRequest

app = FastAPI()
manager = LLMManager()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: LLMRequest):
    try:
        result = await manager.generate(req)
        return result
    except Exception as e:
        return {"error": str(e)}
