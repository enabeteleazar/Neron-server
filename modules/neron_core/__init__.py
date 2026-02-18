import httpx
import os
from agents.base_agent import get_logger

logger = get_logger(__name__)

NERON_LLM_URL = os.getenv("NERON_LLM_URL", "http://neron_llm:5000")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

class LLMAgent:
    async def ask(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{NERON_LLM_URL}/ask",
                json={"prompt": prompt, "model": OLLAMA_MODEL}
            )
            response.raise_for_status()
            return response.json().get("response", "")

class WebAgent:
    async def search(self, query: str) -> str:
        logger.info(f"WebAgent search: {query}")
        return ""
