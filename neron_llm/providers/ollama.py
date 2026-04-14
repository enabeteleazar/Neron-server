import requests
from neron_llm.config import get_llm_config
from neron_llm.core.types import LLMRequest
from .base import BaseProvider


class OllamaProvider(BaseProvider):

    def __init__(self):
        cfg = get_llm_config()
        self.host = cfg.get("host", "http://localhost:11434")
        self.timeout = cfg.get("timeout", 60)

    def generate(self, request: LLMRequest, model: str) -> str:
        try:
            r = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": model,
                    "prompt": request.message,
                    "stream": False
                },
                timeout=self.timeout
            )

            data = r.json()
            return data.get("response", "")

        except Exception as e:
            return f"[OLLAMA ERROR] {str(e)}"
