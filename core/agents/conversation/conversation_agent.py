from __future__ import annotations

from core.self_model.self_model import get_self_model


class ConversationAgent:

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
