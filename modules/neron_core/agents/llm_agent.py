# agents/llm_agent.py
import httpx
import os
from agents.base_agent import BaseAgent, AgentResult

NERON_LLM_URL = os.getenv("NERON_LLM_URL", "http://neron_llm:5000")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60.0"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")


class LLMAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="llm_agent")
        self.logger.info("LLMAgent init avec modele : " + OLLAMA_MODEL)

    async def execute(self, query: str, context_data: str = None, **kwargs) -> AgentResult:
        self.logger.info("LLM query : " + repr(query[:80]))
        start = self._timer()

        prompt = query
        if context_data:
            prompt = (
                "Voici des informations pertinentes :\n\n"
                + context_data
                + "\n\nEn te basant sur ces informations, reponds a la question suivante : "
                + query
            )

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=LLM_TIMEOUT, write=5.0, pool=5.0)
            ) as client:
                response = await client.post(
                    f"{NERON_LLM_URL}/ask",
                    json={"prompt": prompt, "model": OLLAMA_MODEL}
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException:
            return self._failure("llm timeout", latency_ms=self._elapsed_ms(start))
        except httpx.ConnectError:
            return self._failure(f"llm inaccessible a {NERON_LLM_URL}", latency_ms=self._elapsed_ms(start))
        except httpx.HTTPStatusError as e:
            return self._failure(f"llm erreur HTTP {e.response.status_code}", latency_ms=self._elapsed_ms(start))
        except httpx.RequestError as e:
            return self._failure(f"erreur reseau llm : {str(e)}", latency_ms=self._elapsed_ms(start))
        except Exception as e:
            return self._failure(f"erreur inattendue : {str(e)}", latency_ms=self._elapsed_ms(start))

        latency = self._elapsed_ms(start)
        content = data.get("response", "").strip()

        if not content:
            return self._failure("reponse LLM vide", latency_ms=latency)

        return self._success(
            content=content,
            metadata={"model": data.get("model", OLLAMA_MODEL)},
            latency_ms=latency
        )
