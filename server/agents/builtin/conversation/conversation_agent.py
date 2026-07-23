from __future__ import annotations

import time
import unicodedata
from typing import Any

from agents.factory.registry import DynamicAgentRegistry
from agents.runtime.runtime import AgentRuntime
from core.modules.self_model import get_self_model


class ConversationAgent:
    def __init__(
        self,
        registry: DynamicAgentRegistry | None = None,
        runtime: AgentRuntime | None = None,
    ) -> None:
        self.registry = registry or DynamicAgentRegistry()
        self.runtime = runtime or AgentRuntime(registry=self.registry)

    async def delegate_to_registered_agent(self, query: str) -> dict[str, Any] | None:
        record = self.match_registered_agent(query)
        if not record:
            return None

        agent_name = str(record.get("module_name") or record.get("agent_name") or "")
        start = time.monotonic()
        execution = await self.runtime.run_agent(agent_name, query)
        if not execution.ok:
            return {
                "ok": False,
                "agent": agent_name,
                "error": execution.error,
                "execution_time_ms": round((time.monotonic() - start) * 1000, 2),
            }

        return {
            "ok": True,
            "agent": agent_name,
            "response": execution.response,
            "raw": execution.result,
            "execution_time_ms": round((time.monotonic() - start) * 1000, 2),
        }

    def match_registered_agent(self, query: str) -> dict[str, Any] | None:
        query_tokens = self._tokens(query)
        if not query_tokens:
            return None

        best: tuple[int, dict[str, Any] | None] = (0, None)
        for record in self.registry.list_agent_records():
            match_text = str(record.get("match_text") or "")
            record_tokens = self._tokens(match_text)
            overlap = query_tokens & record_tokens
            score = len(overlap)

            distinctive_overlap = {
                token
                for token in overlap
                if len(token) >= 4 and token not in self._generic_agent_tokens()
            }
            if distinctive_overlap and (
                len(overlap) >= 2 or self._has_action_match(query, record_tokens)
            ):
                score += 2

            if score > best[0]:
                best = (score, record)

        score, record = best
        if not record:
            return None

        if score >= 3:
            return record

        return None

    async def greeting(self) -> str:
        return "Salut, je suis là. Que veux-tu faire ?"

    async def thanks(self) -> str:
        return "Avec plaisir."

    async def goodbye(self) -> str:
        return "À bientôt."

    async def status_smalltalk(self) -> str:
        model = get_self_model()

        try:
            model.collect_runtime()
        except Exception:
            pass

        try:
            if hasattr(model, "compute_health"):
                model.compute_health()
        except Exception:
            pass

        data = model.to_dict()
        runtime = data.get("runtime", {})

        cpu = runtime.get("cpu_usage", "N/A")
        ram = runtime.get("ram_usage", "N/A")
        disk = runtime.get("disk_usage", "N/A")
        uptime = runtime.get("uptime")
        raw_health = data.get("health_global", "unknown")
        health = {
            "excellent": "excellent",
            "stable": "stable",
            "stable_with_warning": "stable avec quelques points de vigilance",
            "warning": "en vigilance",
            "critical": "critique",
            "unknown": "inconnu",
        }.get(raw_health, raw_health)
        goal = data.get("active_goal") or "aucun objectif actif"

        uptime_text = self._format_uptime(uptime)

        return (
            f"Oui. État réel actuel : {health}. "
            f"CPU {cpu}%, RAM {ram}%, disque {disk}%. "
            f"Uptime : {uptime_text}. "
            f"Objectif actif : {goal}."
        )

    @staticmethod
    def _format_uptime(seconds) -> str:
        try:
            seconds = int(float(seconds))
        except Exception:
            return "inconnu"

        days = seconds // 86400
        seconds %= 86400
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60

        if days > 0:
            return f"{days}j {hours}h {minutes}min"

        if hours > 0:
            return f"{hours}h {minutes}min"

        return f"{minutes}min"

    @classmethod
    def _tokens(cls, text: str) -> set[str]:
        normalized = cls._normalize(text)
        return {
            token
            for token in normalized.split()
            if len(token) >= 3 and token not in cls._stop_words()
        }

    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize("NFKD", text.lower())
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        cleaned = []
        for char in text:
            cleaned.append(char if char.isalnum() else " ")
        return " ".join("".join(cleaned).split())

    @staticmethod
    def _result_to_text(result: Any) -> str:
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return str(result.get("response") or result)
        if hasattr(result, "content"):
            return str(result.content if getattr(result, "success", True) else result.error)
        return str(result)

    @staticmethod
    def _stop_words() -> set[str]:
        return {
            "avant",
            "avec",
            "dans",
            "des",
            "donc",
            "est",
            "les",
            "pour",
            "que",
            "qui",
            "quoi",
            "reste",
            "restant",
            "temps",
            "une",
        }

    @staticmethod
    def _generic_agent_tokens() -> set[str]:
        return {
            "agent",
            "generated",
            "static",
            "fallback",
            "source",
        }

    @classmethod
    def _has_action_match(cls, query: str, record_tokens: set[str]) -> bool:
        normalized = cls._normalize(query)
        countdown_query = any(
            token in normalized
            for token in ("combien", "reste", "restant", "temps", "avant")
        )
        countdown_agent = bool(record_tokens & {"countdown", "rebours", "event", "evenement"})
        return countdown_query and countdown_agent
