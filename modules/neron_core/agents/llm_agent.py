# modules/neron_core/agents/llm_agent.py

"""
LLMAgent — Wrappeur de neron_llm.
Transforme l'appel LLM existant en agent standardisé.
"""

import httpx
import os
from .base_agent import BaseAgent, AgentResult

NERON_LLM_URL = os.getenv("NERON_LLM_URL", "http://neron_llm:5000")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60.0"))

NERON_SYSTEM_PROMPT = """Tu es Néron, un assistant IA personnel hébergé localement.
Tu es précis, concis et utile. Tu réponds toujours en français sauf demande contraire.
Tu ne mentionnes jamais que tu es basé sur Ollama ou un modèle tiers."""


class LLMAgent(BaseAgent):
    """
    Agent LLM — Génère des réponses via neron_llm.
    Utilisé pour : conversation, synthèse, analyse.
    """

    def __init__(self):
        super().__init__(name="llm_agent")

    async def execute(self, query: str, **kwargs) -> AgentResult:
        """
        Envoie le prompt au LLM et retourne la réponse.

        kwargs:
            system_prompt: override du system prompt
            context_data: données à injecter avant la question (résultats web, etc.)
        """
        system_prompt = kwargs.get("system_prompt", NERON_SYSTEM_PROMPT)
        context_data = kwargs.get("context_data", None)

        final_prompt = query
        if context_data:
            final_prompt = (
                f"{context_data}\n\n"
                f"---\n"
                f"En te basant sur les informations ci-dessus, réponds à cette question :\n"
                f"{query}"
            )

        self.logger.info(f"Appel LLM — modèle : {OLLAMA_MODEL}")
        start = self._timer()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=LLM_TIMEOUT, write=5.0, pool=5.0)
            ) as client:
                response = await client.post(
                    f"{NERON_LLM_URL}/ask",
                    json={
                        "prompt": final_prompt,
                        "model": OLLAMA_MODEL,
                        "system_prompt": system_prompt
                    }
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException:
            return self._failure("LLM timeout", latency_ms=self._elapsed_ms(start))
        except httpx.ConnectError:
            return self._failure(
                f"LLM inaccessible à {NERON_LLM_URL}",
                latency_ms=self._elapsed_ms(start)
            )
        except httpx.HTTPStatusError as e:
            return self._failure(
                f"LLM erreur HTTP {e.response.status_code}",
                latency_ms=self._elapsed_ms(start)
            )
        except httpx.RequestError as e:
            return self._failure(
                f"Erreur réseau LLM : {str(e)}",
                latency_ms=self._elapsed_ms(start)
            )
        except Exception as e:
            return self._failure(
                f"Erreur inattendue LLMAgent : {str(e)}",
                latency_ms=self._elapsed_ms(start)
            )

        response_text = data.get("response", "").strip()
        latency = self._elapsed_ms(start)

        if not response_text:
            return self._failure("LLM a retourné une réponse vide", latency_ms=latency)

        return self._success(
            content=response_text,
            metadata={
                "model": data.get("model", OLLAMA_MODEL),
                "tokens_used": data.get("tokens_used"),
                "generation_time": data.get("generation_time")
            },
            latency_ms=latency
        )
