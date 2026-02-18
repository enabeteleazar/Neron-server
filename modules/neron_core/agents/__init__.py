import httpx
import os
import time
from agents.base_agent import get_logger

logger = get_logger(__name__)

NERON_LLM_URL = os.getenv("NERON_LLM_URL", "http://neron_llm:5000")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")


class AgentResult:
    def __init__(self, success: bool, content: str = "", error: str = "",
                 latency_ms: float = None, metadata: dict = None):
        self.success = success
        self.content = content
        self.error = error
        self.latency_ms = latency_ms
        self.metadata = metadata or {}


class LLMAgent:
    async def ask(self, prompt: str) -> str:
        result = await self.execute(prompt)
        return result.content if result.success else ""

    async def execute(self, query: str, context_data: str = None) -> AgentResult:
        start = time.monotonic()
        prompt = query
        if context_data:
            prompt = f"Contexte:\n{context_data}\n\nQuestion: {query}"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{NERON_LLM_URL}/ask",
                    json={"prompt": prompt, "model": OLLAMA_MODEL}
                )
                response.raise_for_status()
                text = response.json().get("response", "")
                latency = round((time.monotonic() - start) * 1000, 2)
                return AgentResult(success=True, content=text, latency_ms=latency)
        except Exception as e:
            logger.error(f"LLMAgent error: {e}")
            return AgentResult(success=False, error=str(e))


class WebAgent:
    async def search(self, query: str) -> str:
        result = await self.execute(query)
        return result.content if result.success else ""

    async def execute(self, query: str) -> AgentResult:
        # Placeholder — à implémenter avec une vraie API de recherche
        logger.info(f"WebAgent search: {query}")
        return AgentResult(success=False, error="WebAgent non implémenté",
                           metadata={"sources": [], "total_results": 0})
