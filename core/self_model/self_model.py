from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil


STATE_PATH = Path("/etc/neron/data/self_model_state.json")


@dataclass
class SelfModel:
    identity: dict[str, Any] = field(default_factory=dict)
    runtime: dict[str, Any] = field(default_factory=dict)
    services: dict[str, str] = field(default_factory=dict)
    cognitive_state: dict[str, Any] = field(default_factory=dict)

    diagnostics: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    active_goal: str = "maintenir la stabilité système"

    health_realtime: str = "unknown"
    health_historical: str = "unknown"
    health_global: str = "unknown"

    last_update: float | None = None

    def __post_init__(self) -> None:
        self.identity = {
            "name": "Néron",
            "role": "Assistant IA personnel",
            "language": "fr",
            "version": "0.3.0",
        }

    def collect_runtime(self) -> None:
        disk = shutil.disk_usage("/")

        self.runtime = {
            "cpu_usage": psutil.cpu_percent(interval=0.2),
            "ram_usage": psutil.virtual_memory().percent,
            "disk_usage": round((disk.used / disk.total) * 100, 2),
            "uptime": round(time.time() - psutil.boot_time(), 2),
        }

    def collect_services(self) -> None:
        tracked_services = [
            "neron-core",
            "neron-llm",
            "neron-doctor",
            "neron-cognitive-loop",
            "neron-self-model-loop",
        ]

        self.services = {}

        for service in tracked_services:
            self.services[service] = self._systemctl_is_active(service)

    def _systemctl_is_active(self, service: str) -> str:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=2,
            )

            status = result.stdout.strip()

            if not status:
                return "unknown"

            return status

        except Exception:
            return "unknown"

    def compute_health(self) -> None:
        self.health_realtime = "excellent"
        self.health_historical = "excellent"

        cpu_usage = self.runtime.get("cpu_usage", 0)
        ram_usage = self.runtime.get("ram_usage", 0)
        disk_usage = self.runtime.get("disk_usage", 0)

        if cpu_usage >= 90:
            self.health_realtime = "warning"

        if ram_usage >= 90:
            self.health_realtime = "warning"

        if disk_usage >= 90:
            self.health_realtime = "warning"

        critical_services = [
            "neron-core",
            "neron-llm",
            "neron-doctor",
            "neron-self-model-loop",
        ]

        for service in critical_services:
            if self.services.get(service) != "active":
                self.health_realtime = "warning"

        if self.health_realtime == "excellent":
            self.health_global = "stable"
        else:
            self.health_global = "stable_with_warning"

    def compute_cognitive_state(self) -> None:
        self.cognitive_state = {
            "self_model_loop": self.services.get("neron-self-model-loop") == "active",
            "autonomous_loop": self.services.get("neron-cognitive-loop") == "active",
            "core_online": self.services.get("neron-core") == "active",
            "llm_online": self.services.get("neron-llm") == "active",
            "doctor_online": self.services.get("neron-doctor") == "active",
            "decision_engine": True,
            "memory_online": True,
            "reasoning_online": True,
        }

    def compute_diagnostics(self) -> None:
        self.diagnostics = []

        cpu_usage = self.runtime.get("cpu_usage", 0)
        ram_usage = self.runtime.get("ram_usage", 0)
        disk_usage = self.runtime.get("disk_usage", 0)

        if cpu_usage >= 90:
            self.diagnostics.append("Charge CPU élevée.")

        if ram_usage >= 90:
            self.diagnostics.append("Utilisation RAM élevée.")

        if disk_usage >= 90:
            self.diagnostics.append("Espace disque critique.")

        if self.services.get("neron-core") != "active":
            self.diagnostics.append("Le service neron-core est inactif.")

        if self.services.get("neron-llm") != "active":
            self.diagnostics.append("Le service neron-llm est inactif.")

        if self.services.get("neron-doctor") != "active":
            self.diagnostics.append("Le service neron-doctor est inactif.")

        if self.services.get("neron-self-model-loop") != "active":
            self.diagnostics.append("Le Self-Model loop est inactif.")

        if self.services.get("neron-cognitive-loop") != "active":
            self.diagnostics.append("La boucle cognitive autonome est inactive.")

    def compute_recommendations(self) -> None:
        self.recommendations = []

        cpu_usage = self.runtime.get("cpu_usage", 0)
        ram_usage = self.runtime.get("ram_usage", 0)
        disk_usage = self.runtime.get("disk_usage", 0)

        if cpu_usage >= 90:
            self.recommendations.append(
                "Réduire la charge LLM ou basculer vers un modèle plus léger."
            )

        if ram_usage >= 90:
            self.recommendations.append(
                "Libérer de la mémoire ou réduire les services non essentiels."
            )

        if disk_usage >= 90:
            self.recommendations.append(
                "Nettoyer les logs, caches ou anciens paquets système."
            )

        if self.services.get("neron-core") != "active":
            self.recommendations.append("Redémarrer le service neron-core.")

        if self.services.get("neron-llm") != "active":
            self.recommendations.append("Redémarrer le service neron-llm.")

        if self.services.get("neron-doctor") != "active":
            self.recommendations.append("Redémarrer le service neron-doctor.")

        if self.services.get("neron-self-model-loop") != "active":
            self.recommendations.append("Démarrer le service neron-self-model-loop.")

        if self.services.get("neron-cognitive-loop") != "active":
            self.recommendations.append("Démarrer le service neron-cognitive-loop.")

    def update_from_event(self, event) -> None:
        try:
            self.last_event = {
                "type": getattr(event, "type", None),
                "source": getattr(event, "source", None),
                "event_id": getattr(event, "event_id", None),
            }
        except Exception:
            self.last_event = {"raw": str(event)}

    def set_agents_available(self, agents) -> None:
        try:
            self.agents_available = list(agents)
        except Exception:
            self.agents_available = []

    def set_last_intent(self, intent: str, confidence: float | None = None) -> None:
        self.last_intent = {
            "intent": intent,
            "confidence": confidence,
        }

    def record_agent_run(self, agent_name: str, success: bool = True) -> None:
        if not hasattr(self, "agent_runs"):
            self.agent_runs = {}

        current = self.agent_runs.get(
            agent_name,
            {"runs": 0, "failures": 0},
        )

        current["runs"] += 1

        if not success:
            current["failures"] += 1

        self.agent_runs[agent_name] = current

    def _merge_state(self, patch: dict) -> None:
        data = load_self_model_state()
        data.update(patch)

        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = STATE_PATH.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(STATE_PATH)

    def set_last_intent(self, intent: str, confidence: float | None = None) -> None:
        data = load_self_model_state()

        event_count = int(data.get("event_count", 0)) + 1

        intent_entry = {
            "intent": intent,
            "confidence": confidence,
            "timestamp": time.time(),
        }

        history = data.get("intent_history", [])

        if not isinstance(history, list):
            history = []

        history.append(intent_entry)
        history = history[-5:]

        self.last_intent = intent_entry
        self.intent_history = history
        self.event_count = event_count

        self._merge_state(
            {
                "last_intent": intent_entry,
                "intent_history": history,
                "event_count": event_count,
            }
        )

    def set_last_agent(self, agent_name: str) -> None:
        self.last_agent = {
            "agent": agent_name,
            "timestamp": time.time(),
        }
        self._merge_state({"last_agent": self.last_agent})

    def set_last_error(self, error: str | None) -> None:
        self.last_error = {
            "error": error,
            "timestamp": time.time(),
        }
        self._merge_state({"last_error": self.last_error})

    def set_agents_available(self, agents) -> None:
        try:
            self.agents_available = list(agents)
        except Exception:
            self.agents_available = []

        self._merge_state({"agents_available": self.agents_available})

    def _format_duration(self, seconds: float | int | None) -> str:
        if seconds is None:
            return "inconnu"

        try:
            seconds = int(seconds)
        except Exception:
            return "inconnu"

        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)

        parts = []

        if days:
            parts.append(f"{days}j")

        if hours:
            parts.append(f"{hours}h")

        if minutes or not parts:
            parts.append(f"{minutes}min")

        return " ".join(parts)

    def _state_age_text(self, last_update: float | None) -> str:
        if not last_update:
            return "inconnu"

        age = max(0, time.time() - float(last_update))

        if age < 60:
            return f"mis à jour il y a {int(age)} secondes"

        if age < 3600:
            return f"mis à jour il y a {int(age // 60)} minutes"

        return f"mis à jour il y a {int(age // 3600)} heures"

    def summary(self) -> str:
        data = load_self_model_state()

        runtime = data.get("runtime", {})
        cognitive = data.get("cognitive_state", {})
        services = data.get("services", {})
        diagnostics = data.get("diagnostics", [])
        recommendations = data.get("recommendations", [])
        last_intent = data.get("last_intent", {})
        last_agent_data = data.get("last_agent", {})
        last_error_data = data.get("last_error", {})
        agents = data.get("agents_available", [])
        intent_history = data.get("intent_history", [])
        event_count = data.get("event_count", 0)
        last_update = data.get("last_update")

        health_global = data.get("health_global", "unknown")
        health_realtime = data.get("health_realtime", "unknown")
        health_historical = data.get("health_historical", "unknown")

        uptime = runtime.get("uptime")
        uptime_text = self._format_duration(uptime)
        state_age = self._state_age_text(last_update)
        cpu = runtime.get("cpu_usage")
        ram = runtime.get("ram_usage")
        disk = runtime.get("disk_usage")

        autonomous = cognitive.get("autonomous_loop", False)
        loop_state = "active" if autonomous else "inactive"

        watchdog_score = 100.0 if health_global == "stable" else 75.0
        watchdog_state = "🟢 Excellent" if watchdog_score >= 90 else "🟠 Warning"

        last_intent_name = (
            last_intent.get("intent")
            if isinstance(last_intent, dict)
            else None
        )

        last_agent_name = (
            last_agent_data.get("agent")
            if isinstance(last_agent_data, dict)
            else None
        )

        last_error_text = (
            last_error_data.get("error")
            if isinstance(last_error_data, dict)
            else None
        ) or "aucune"

        active_agents = ", ".join(agents) if agents else "aucun"

        diagnostics_text = (
            "\n".join(f"  • {item}" for item in diagnostics)
            if diagnostics
            else "aucun"
        )

        recommendations_text = (
            "\n".join(f"  • {item}" for item in recommendations)
            if recommendations
            else "aucune"
        )

        active_services = [
            name
            for name, status in services.items()
            if status == "active"
        ]

        services_text = ", ".join(active_services) if active_services else "aucun"

        if isinstance(intent_history, list) and intent_history:
            history_items = []
            for item in intent_history[-5:]:
                if isinstance(item, dict):
                    name = item.get("intent", "unknown")
                    conf = item.get("confidence")
                    history_items.append(f"{name} ({conf})")
            intent_history_text = ", ".join(history_items) if history_items else "aucun"
        else:
            intent_history_text = "aucun"

        summary_line = (
            f"Néron est {health_global}. "
            f"CPU {cpu}%, RAM {ram}%, disque {disk}%. "
            f"Boucle cognitive {loop_state}."
        )

        return f"""{summary_line}

État interne de Néron :
- Santé globale : {health_global}
- Santé temps réel : {health_realtime}
- Santé historique : {health_historical}
- Uptime : {uptime_text}
- CPU : {cpu}%
- RAM : {ram}%
- Disque : {disk}%
- Watchdog : {watchdog_state} ({watchdog_score}/100)
- Boucle cognitive : {loop_state}
- Dernière intention : {last_intent_name}
- Historique intents : {intent_history_text}
- Compteur événements : {event_count}
- État : {state_age}
- Dernier agent : {last_agent_name}
- Agents disponibles : {active_agents}
- Services actifs : {services_text}
- Diagnostics : {diagnostics_text}
- Recommandations : {recommendations_text}
- Dernière erreur : {last_error_text}"""

    def refresh(self) -> None:
        self.collect_runtime()
        self.collect_services()
        self.compute_health()
        self.compute_cognitive_state()
        self.compute_diagnostics()
        self.compute_recommendations()
        self.last_update = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "runtime": self.runtime,
            "services": self.services,
            "health_realtime": self.health_realtime,
            "health_historical": self.health_historical,
            "health_global": self.health_global,
            "active_goal": self.active_goal,
            "cognitive_state": self.cognitive_state,
            "diagnostics": self.diagnostics,
            "recommendations": self.recommendations,
            "last_update": self.last_update,
            "last_event": getattr(self, "last_event", None),
            "last_intent": getattr(self, "last_intent", None),
            "agents_available": getattr(self, "agents_available", []),
            "agent_runs": getattr(self, "agent_runs", {}),
        }

    def save_state(self) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

        existing = {}

        if STATE_PATH.exists():
            try:
                existing = json.loads(
                    STATE_PATH.read_text(encoding="utf-8")
                )
            except Exception:
                existing = {}

        data = existing | self.to_dict()

        for key in (
            "last_intent",
            "intent_history",
            "event_count",
            "last_agent",
            "last_error",
            "agents_available",
        ):
            if key in existing and data.get(key) in (None, [], {}, 0):
                data[key] = existing[key]

        tmp_path = STATE_PATH.with_suffix(".json.tmp")

        tmp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        tmp_path.replace(STATE_PATH)


def load_self_model_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        model = SelfModel()
        model.refresh()
        model.save_state()
        return model.to_dict()

    try:
        return json.loads(
            STATE_PATH.read_text(encoding="utf-8")
        )
    except Exception:
        model = SelfModel()
        model.refresh()
        model.save_state()
        return model.to_dict()


_SELF_MODEL: SelfModel | None = None


def get_self_model() -> SelfModel:
    global _SELF_MODEL

    if _SELF_MODEL is None:
        _SELF_MODEL = SelfModel()

    return _SELF_MODEL
