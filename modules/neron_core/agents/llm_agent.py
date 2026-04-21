# agents/llm_agent.py
# Neron Core - Agent LLM (appel direct Ollama, sans neron_llm intermédiaire)

import httpx
import os
import json
from agents.base_agent import BaseAgent, AgentResult

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120.0"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

SYSTEM_PROMPT = os.getenv("NERON_SYSTEM_PROMPT", """Tu es Néron, un assistant IA personnel installé sur Homebox.
Tu es concis, direct et utile. Tu réponds toujours en français.
Tu as accès à la mémoire des conversations passées, à l'heure, à la météo et à Home Assistant.
Tu n'es pas un assistant générique — tu es Néron, l'assistant personnel de ton utilisateur.
Ne te présente jamais comme un modèle de langage ou une IA générique.""")


def _build_prompt(query: str, context_data: str = None) -> str:
    if not context_data:
        return query
    if context_data.startswith("Historique"):
        return (
            "Tu es Néron, un assistant IA personnel. "
            "Voici le contexte de notre conversation :\n\n"
            + context_data
            + "\n\nRéponds maintenant à cette nouvelle question en tenant compte du contexte : "
            + query
        )
    return (
        "Voici des informations pertinentes :\n\n"
        + context_data
        + "\n\nEn te basant sur ces informations, réponds à la question suivante : "
        + query
    )


class LLMAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="llm_agent")
        self.logger.info(f"LLMAgent init — Ollama direct : {OLLAMA_HOST} | modèle : {OLLAMA_MODEL}")

    async def execute(self, query: str, context_data: str = None, **kwargs) -> AgentResult:
        self.logger.info("LLM query : " + repr(query[:80]))
        start = self._timer()
        prompt = _build_prompt(query, context_data)
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=LLM_TIMEOUT, write=5.0, pool=5.0)
            ) as client:
                response = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException:
            return self._failure("ollama timeout", latency_ms=self._elapsed_ms(start))
        except httpx.ConnectError:
            return self._failure(f"ollama inaccessible à {OLLAMA_HOST}", latency_ms=self._elapsed_ms(start))
        except httpx.HTTPStatusError as e:
            return self._failure(f"ollama erreur HTTP {e.response.status_code}", latency_ms=self._elapsed_ms(start))
        except httpx.RequestError as e:
            return self._failure(f"erreur réseau ollama : {str(e)}", latency_ms=self._elapsed_ms(start))
        except Exception as e:
            return self._failure(f"erreur inattendue : {str(e)}", latency_ms=self._elapsed_ms(start))

        latency = self._elapsed_ms(start)
        content = data.get("response", "").strip()
        if not content:
            return self._failure("réponse Ollama vide", latency_ms=latency)

        return self._success(
            content=content,
            metadata={
                "model": OLLAMA_MODEL,
                "tokens_used": data.get("eval_count"),
                "generation_time_s": round(data.get("total_duration", 0) / 1e9, 2)
            },
            latency_ms=latency
        )

    async def stream(self, query: str, context_data: str = None):
        """Streaming token par token directement depuis Ollama"""
        prompt = _build_prompt(query, context_data)
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": True}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=LLM_TIMEOUT, write=5.0, pool=5.0)
        ) as client:
            async with client.stream("POST", f"{OLLAMA_HOST}/api/generate", json=payload) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except Exception:
                        continue

    async def reload(self) -> bool:
        """Recharge la connexion Ollama"""
        try:
            return await self.check_connection()
        except Exception as e:
            logger.error(f"LLM reload error: {e}")
            return False

    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{OLLAMA_HOST}/api/tags")
                return r.status_code == 200
        except Exception:
            return False
