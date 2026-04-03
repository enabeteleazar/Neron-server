# agents/llm_agent.py
# Neron Core - Agent LLM
#
# Intégration module personality v7 :
# - build_system_prompt() remplace le SYSTEM_PROMPT statique du neron.yaml
# - Le system_prompt est injecté dans chaque requête Ollama via le champ "system"
# - Fallback transparent sur l'ancien SYSTEM_PROMPT si le module est indisponible

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from agents.base_agent import BaseAgent, AgentResult
from config import settings

# ── Constantes ────────────────────────────────────────────────────────────────

OLLAMA_HOST  = settings.OLLAMA_HOST
LLM_TIMEOUT  = settings.LLM_TIMEOUT
OLLAMA_MODEL = settings.OLLAMA_MODEL

_STATIC_SYSTEM_PROMPT = settings.SYSTEM_PROMPT

# ── Import personality au niveau module ───────────────────────────────────────
# FIX: import tenté une seule fois au chargement du module au lieu de
# répéter le try/import dans chaque appel à _get_system_prompt().

try:
    from personality import build_system_prompt as _build_personality_prompt
    _PERSONALITY_AVAILABLE = True
except Exception:
    _build_personality_prompt  = None  # type: ignore[assignment]
    _PERSONALITY_AVAILABLE     = False


def _get_system_prompt(user_context: str = "") -> tuple[str, bool]:
    """
    Retourne (system_prompt, personality_active).
    - Nominal  : généré dynamiquement par le module personality
    - Fallback : SYSTEM_PROMPT statique depuis neron.yaml
    FIX: retourne un bool pour indiquer si le module personality est actif,
    permettant de renseigner correctement personality_active dans metadata.
    """
    if _PERSONALITY_AVAILABLE and _build_personality_prompt is not None:
        try:
            return _build_personality_prompt(user_context=user_context), True
        except Exception:
            pass
    return _STATIC_SYSTEM_PROMPT, False


def _build_messages(query: str, context_data: str | None = None) -> list[dict]:
    """
    Construit la liste de messages au format chat Ollama.
    FIX: context_data annoté str | None au lieu de str = None.
    """
    system_prompt, _ = _get_system_prompt()
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


# ── Agent ─────────────────────────────────────────────────────────────────────


class LLMAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="llm_agent")
        self.logger.info(
            "LLMAgent init — Ollama : %s | modèle : %s | personality : %s",
            OLLAMA_HOST,
            OLLAMA_MODEL,
            "module v7" if _PERSONALITY_AVAILABLE else "fallback statique",
        )

    async def execute(
        self,
        query:        str,
        context_data: str | None = None,
        **kwargs,
    ) -> AgentResult:
        # FIX: self.logger au lieu de concaténation de chaîne
        self.logger.info("LLM query : %r", query[:80])
        start = self._timer()

        _, personality_active = _get_system_prompt()
        messages = _build_messages(query, context_data)

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
                latency_ms=self._elapsed_ms(start),
            )
        except httpx.HTTPStatusError as e:
            return self._failure(
                f"ollama erreur HTTP {e.response.status_code}",
                latency_ms=self._elapsed_ms(start),
            )
        except httpx.RequestError as e:
            return self._failure(
                f"erreur réseau ollama : {e}",
                latency_ms=self._elapsed_ms(start),
            )
        except Exception as e:
            return self._failure(
                f"erreur inattendue : {e}",
                latency_ms=self._elapsed_ms(start),
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
                # FIX: personality_active reflète l'état réel du module
                "personality_active": personality_active,
            },
            latency_ms=latency,
        )

    async def stream(
        self,
        query:        str,
        context_data: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Streaming token par token via /api/chat.
        FIX: gestion d'erreurs ajoutée — les exceptions sont loggées
        et le stream s'arrête proprement au lieu de propager une exception brute.
        """
        messages = _build_messages(query, context_data)
        payload  = {"model": OLLAMA_MODEL, "messages": messages, "stream": True}

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=5.0, read=LLM_TIMEOUT, write=5.0, pool=5.0
                )
            ) as client:
                async with client.stream(
                    "POST", f"{OLLAMA_HOST}/api/chat", json=payload
                ) as response:
                    response.raise_for_status()
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
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException:
            self.logger.warning("stream : ollama timeout")
        except httpx.ConnectError:
            self.logger.error("stream : ollama inaccessible à %s", OLLAMA_HOST)
        except httpx.HTTPStatusError as e:
            self.logger.error("stream : erreur HTTP %s", e.response.status_code)
        except Exception as e:
            self.logger.exception("stream : erreur inattendue : %s", e)

    async def reload(self) -> bool:
        """Recharge la connexion Ollama."""
        try:
            return await self.check_connection()
        except Exception as e:
            # FIX: self.logger au lieu du logger module-level
            self.logger.error("LLM reload error : %s", e)
            return False

    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{OLLAMA_HOST}/api/tags")
                return r.status_code == 200
        except Exception:
            return False
