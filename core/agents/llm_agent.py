# agents/llm_agent.py
# Neron Core - Agent LLM
#
# Intégration module personality v7 :
# - build_system_prompt() remplace le SYSTEM_PROMPT statique du neron.yaml
# - Le system_prompt est injecté dans chaque requête Ollama via le champ "system"
# - Fallback transparent sur l'ancien SYSTEM_PROMPT si le module est indisponible

import httpx
import json
import logging
from config import settings
from agents.base_agent import BaseAgent, AgentResult

OLLAMA_HOST  = settings.OLLAMA_HOST
LLM_TIMEOUT  = settings.LLM_TIMEOUT
OLLAMA_MODEL = settings.OLLAMA_MODEL

# Prompt statique de secours (lu depuis neron.yaml, inchangé)
_STATIC_SYSTEM_PROMPT = settings.SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _get_system_prompt(user_context: str = "") -> str:
    """
    Retourne le system prompt actif.
    - Nominal  : généré dynamiquement par le module personality (mood, energy, traits…)
    - Fallback : SYSTEM_PROMPT statique depuis neron.yaml si le module est indisponible
    """
    try:
        from personality import build_system_prompt
        return build_system_prompt(user_context=user_context)
    except Exception as e:
        logger.warning(f"[LLM] Module personality indisponible, fallback statique : {e}")
        return _STATIC_SYSTEM_PROMPT


def _build_messages(query: str, context_data: str = None) -> list[dict]:
    """
    Construit la liste de messages au format chat Ollama.
    Le system prompt est injecté en premier message de rôle 'system'.
    Le contexte mémoire est fusionné dans le message utilisateur si présent.
    """
    # Contexte utilisateur pour enrichir le prompt système (ex: infos session)
    system_prompt = _get_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]

    if context_data:
        if context_data.startswith("Historique"):
            user_content = (
                "Voici le contexte de notre conversation :\n\n"
                + context_data
                + "\n\nRéponds maintenant à cette nouvelle question "
                  "en tenant compte du contexte : "
                + query
            )
        else:
            user_content = (
                "Voici des informations pertinentes :\n\n"
                + context_data
                + "\n\nEn te basant sur ces informations, "
                  "réponds à la question suivante : "
                + query
            )
    else:
        user_content = query

    messages.append({"role": "user", "content": user_content})
    return messages


class LLMAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="llm_agent")
        self.logger.info(
            f"LLMAgent init — Ollama : {OLLAMA_HOST} | modèle : {OLLAMA_MODEL} | "
            "personality : module v7"
        )

    async def execute(
        self, query: str, context_data: str = None, **kwargs
    ) -> AgentResult:
        self.logger.info("LLM query : " + repr(query[:80]))
        start = self._timer()

        messages = _build_messages(query, context_data)

        # Ollama /api/chat pour le format messages (system + user)
        payload = {
            "model":    OLLAMA_MODEL,
            "messages": messages,
            "stream":   False,
        }

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=5.0, read=LLM_TIMEOUT, write=5.0, pool=5.0
                )
            ) as client:
                response = await client.post(
                    f"{OLLAMA_HOST}/api/chat", json=payload
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException:
            return self._failure("ollama timeout", latency_ms=self._elapsed_ms(start))
        except httpx.ConnectError:
            return self._failure(
                f"ollama inaccessible à {OLLAMA_HOST}",
                latency_ms=self._elapsed_ms(start)
            )
        except httpx.HTTPStatusError as e:
            return self._failure(
                f"ollama erreur HTTP {e.response.status_code}",
                latency_ms=self._elapsed_ms(start)
            )
        except httpx.RequestError as e:
            return self._failure(
                f"erreur réseau ollama : {str(e)}",
                latency_ms=self._elapsed_ms(start)
            )
        except Exception as e:
            return self._failure(
                f"erreur inattendue : {str(e)}",
                latency_ms=self._elapsed_ms(start)
            )

        latency = self._elapsed_ms(start)
        content = data.get("message", {}).get("content", "").strip()
        if not content:
            return self._failure("réponse Ollama vide", latency_ms=latency)

        return self._success(
            content=content,
            metadata={
                "model":              OLLAMA_MODEL,
                "tokens_used":        data.get("eval_count"),
                "generation_time_s":  round(data.get("total_duration", 0) / 1e9, 2),
                "personality_active": True,
            },
            latency_ms=latency,
        )

    async def stream(self, query: str, context_data: str = None):
        """Streaming token par token via /api/chat (format messages)."""
        messages = _build_messages(query, context_data)
        payload  = {"model": OLLAMA_MODEL, "messages": messages, "stream": True}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0, read=LLM_TIMEOUT, write=5.0, pool=5.0
            )
        ) as client:
            async with client.stream(
                "POST", f"{OLLAMA_HOST}/api/chat", json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data  = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except Exception:
                        continue

    async def reload(self) -> bool:
        """Recharge la connexion Ollama."""
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
