"""Client HTTP vers le service llm.

Aucun import du code du service llm lui-même (ni son LLMManager en
process, ni ses providers) — uniquement des appels HTTP à son contrat
public (POST /llm/generate), exactement comme GoalClient pour goal.

Le service llm garantit déjà (phase 5, plancher + liste blanche) que
task_type="code"/"reasoning"/"agent" reste local à Ollama sauf
configuration future explicite. Ce client ne duplique pas cette logique
de sécurité — il lui fait confiance, comme n'importe quel appelant HTTP
du contrat public.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from server.common.auth import api_key_headers
from server.common.http import async_client

logger = logging.getLogger("neron.llm_client")


class LLMClientError(RuntimeError):
    """Erreur générique d'appel au service llm (réseau, timeout, 5xx)."""


def _default_base_url() -> str:
    return os.getenv("NERON_LLM_URL", "http://127.0.1.2:8765").rstrip("/")


def _default_api_key() -> str:
    return os.getenv("NERON_API_KEY", "").strip()


class LLMClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 300.0,  # génération de code potentiellement longue (modèle 14B local)
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or _default_base_url()).rstrip("/")
        self.api_key = api_key if api_key is not None else _default_api_key()
        self.timeout = timeout
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return async_client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=api_key_headers(self.api_key),
            transport=self._transport,
        )

    async def generate(
        self,
        *,
        prompt: str,
        task_type: str = "chat",
        context: dict[str, str] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Appelle POST /llm/generate. Renvoie {result, model_used, latency_ms, warning}."""
        payload: dict[str, Any] = {"task_type": task_type, "prompt": prompt}
        if context:
            payload["context"] = context
        if request_id:
            payload["request_id"] = request_id

        try:
            async with self._client() as client:
                response = await client.request("POST", "/llm/generate", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMClientError(f"Timeout appelant llm /llm/generate (task_type={task_type})") from exc
        except httpx.RequestError as exc:
            raise LLMClientError(f"Erreur réseau appelant llm /llm/generate: {exc}") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMClientError(
                f"llm /llm/generate -> {response.status_code}: {response.text[:300]}"
            ) from exc

        return response.json()

    async def generate_code(self, prompt: str, *, request_id: str | None = None) -> str:
        """Raccourci : génération de code (task_type='code' — Ollama garanti par le
        plancher de sécurité du service llm, phase 5)."""
        result = await self.generate(prompt=prompt, task_type="code", request_id=request_id)
        return str(result.get("result") or "")


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
