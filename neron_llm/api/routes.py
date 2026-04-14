from fastapi import APIRouter
from neron_llm.core.manager import LLMManager
from neron_llm.core.types import LLMRequest

router = APIRouter()
manager = LLMManager()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/chat")
def chat(req: LLMRequest):
    return manager.handle(req)
