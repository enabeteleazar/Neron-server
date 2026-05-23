from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil
import os
import platform
import socket
import sys


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

    def update_from_event(self, event: Any) -> None:
        event_type = (
            getattr(event, "type", None)
            or getattr(event, "event_type", None)
            or "unknown"
        )

        source = getattr(event, "source", None) or "unknown"
        event_id = getattr(event, "event_id", None) or getattr(event, "id", None)

        payload = getattr(event, "payload", None)
        details = getattr(event, "details", None)

        if payload is None:
            payload = {}

        if details is None:
            details = {}

        if not isinstance(payload, dict):
            payload = {"raw": str(payload)}

        if not isinstance(details, dict):
            details = {"raw": str(details)}

        data = load_self_model_state()

        event_count = int(data.get("event_count", 0)) + 1

        last_event = {
            "type": event_type,
            "source": source,
            "event_id": event_id,
            "payload_keys": list(payload.keys()),
            "details": details,
            "timestamp": time.time(),
        }

        recent_events = data.get("recent_events", [])
        if not isinstance(recent_events, list):
            recent_events = []

        recent_events.append(last_event)
        recent_events = recent_events[-10:]

        recent_activity = data.get("recent_activity", [])
        recent_events = data.get("recent_events", [])
        if not isinstance(recent_activity, list):
            recent_activity = []

        activity = self._activity_from_event(event_type, source, payload, details)

        if activity:
            recent_activity.append({
                "activity": activity,
                "timestamp": time.time(),
            })

        recent_activity = recent_activity[-8:]

        patch: dict[str, Any] = {
            "last_event": last_event,
            "recent_events": recent_events,
            "recent_activity": recent_activity,
            "event_count": event_count,
        }

        if event_type == "intent.detected":
            intent_name = (
                details.get("intent")
                or payload.get("intent")
                or "unknown"
            )

            intent_name = self._normalize_intent_name(intent_name)

            confidence = (
                details.get("confidence")
                or payload.get("confidence")
                or payload.get("confidence_score")
            )

            intent_entry = {
                "intent": intent_name,
                "confidence": confidence,
                "timestamp": time.time(),
            }

            history = data.get("intent_history", [])
            if not isinstance(history, list):
                history = []

            history.append(intent_entry)
            history = history[-5:]

            patch["last_intent"] = intent_entry
            patch["intent_history"] = history

        elif event_type in ("agent.selected", "agent.executed"):
            agent_name = (
                details.get("agent")
                or payload.get("agent")
                or payload.get("agent_name")
                or "unknown"
            )

            patch["last_agent"] = {
                "agent": agent_name,
                "timestamp": time.time(),
            }

        elif event_type in ("system.service.error", "agent.error", "self.repair.failed"):
            error = (
                details.get("error")
                or payload.get("error")
                or payload.get("message")
                or f"Erreur événement : {event_type}"
            )

            patch["last_error"] = {
                "error": error,
                "timestamp": time.time(),
            }

        elif event_type in ("system.service.started", "system.service.recovered"):
            patch["last_error"] = {
                "error": None,
                "timestamp": time.time(),
            }

        self._merge_state(patch)

    def _normalize_intent_name(self, intent: Any) -> str:
        value = getattr(intent, "value", None)

        if value:
            return str(value)

        text = str(intent)

        if text.startswith("Intent."):
            return text.replace("Intent.", "").lower()

        return text

    def _activity_from_event(
        self,
        event_type: str,
        source: str,
        payload: dict[str, Any],
        details: dict[str, Any],
    ) -> str | None:
        if event_type == "user.message.received":
            return "message utilisateur reçu"

        if event_type == "intent.detected":
            intent_name = (
                details.get("intent")
                or payload.get("intent")
                or "unknown"
            )

            return f"Intent détecté : {self._normalize_intent_name(intent_name)}"

        if event_type == "agent.selected":
            agent_name = (
                details.get("agent")
                or payload.get("agent")
                or payload.get("agent_name")
                or "unknown"
            )

            return f"Agent sélectionné : {agent_name}"

        if event_type == "agent.executed":
            agent_name = (
                details.get("agent")
                or payload.get("agent")
                or payload.get("agent_name")
                or "unknown"
            )

            return f"Agent exécuté : {agent_name}"

        if event_type == "response.ready":
            return "réponse prête"

        if event_type == "system.service.error":
            service = (
                details.get("service")
                or payload.get("service")
                or source
            )

            return f"Erreur service : {service}"

        if event_type == "system.service.started":
            service = (
                details.get("service")
                or payload.get("service")
                or source
            )

            return f"Service démarré : {service}"

        if event_type.startswith("self.repair"):
            return f"SelfRepair : {event_type}"

        return f"Événement : {event_type}"

    def collect_runtime(self) -> None:
        disk = shutil.disk_usage("/")
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        boot_time = psutil.boot_time()
        uptime_seconds = round(time.time() - boot_time, 2)

        try:
            load_average = list(os.getloadavg())
        except (AttributeError, OSError):
            load_average = []

        process = psutil.Process()

        self.runtime = {
            "cpu_usage": psutil.cpu_percent(interval=0.2),
            "ram_usage": memory.percent,
            "disk_usage": round((disk.used / disk.total) * 100, 2),
            "swap_usage": swap.percent,
            "uptime": uptime_seconds,
            "uptime_seconds": uptime_seconds,
            "boot_time": boot_time,
            "load_average": load_average,
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "process_pid": process.pid,
            "process_memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
        }

    def collect_services(self) -> None:
        critical = [
            "neron-core",
            "neron-llm",
            "neron-doctor",
            "neron-cognitive-loop",
            "neron-self-model-loop",
            "neron-cognitive-daemon",
        ]

        optional = [
            "neron-homeassistant",
            "neron-kula",
            "neron-stt",
            "neron-vocal",
        ]

        tracked = critical + optional

        statuses = {
            name: self._systemctl_is_active(name)
            for name in tracked
        }

        critical_statuses = {
            name: statuses.get(name, "unknown")
            for name in critical
        }

        optional_statuses = {
            name: statuses.get(name, "unknown")
            for name in optional
        }

        active_count = sum(1 for status in statuses.values() if status == "active")
        inactive_count = sum(1 for status in statuses.values() if status != "active")
        critical_inactive = [
            name for name, status in critical_statuses.items()
            if status != "active"
        ]
        optional_inactive = [
            name for name, status in optional_statuses.items()
            if status != "active"
        ]

        self.services = {
            "items": statuses,
            "critical": critical_statuses,
            "optional": optional_statuses,
            "summary": {
                "total": len(statuses),
                "active": active_count,
                "inactive": inactive_count,
                "critical_total": len(critical_statuses),
                "critical_inactive": len(critical_inactive),
                "critical_inactive_services": critical_inactive,
                "optional_total": len(optional_statuses),
                "optional_inactive": len(optional_inactive),
                "optional_inactive_services": optional_inactive,
                "all_critical_active": len(critical_inactive) == 0,
                "all_active": inactive_count == 0,
            },
        }

    def _systemctl_is_active(self, service: str) -> str:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"

    def compute_health(self) -> None:
        self.health_realtime = "excellent"
        self.health_historical = "excellent"

        if self.runtime.get("cpu_usage", 0) >= 90:
            self.health_realtime = "warning"
        if self.runtime.get("ram_usage", 0) >= 90:
            self.health_realtime = "warning"
        if self.runtime.get("disk_usage", 0) >= 90:
            self.health_realtime = "warning"

        critical = ["neron-core", "neron-llm", "neron-doctor", "neron-self-model-loop"]
        for service in critical:
            if self.services.get("items", {}).get(service) != "active":
                self.health_realtime = "warning"

        self.health_global = "stable" if self.health_realtime == "excellent" else "stable_with_warning"

    def compute_cognitive_state(self) -> None:
        self.cognitive_state = {
            "self_model_loop": self.services.get("items", {}).get("neron-self-model-loop") == "active",
            "autonomous_loop": self.services.get("items", {}).get("neron-cognitive-loop") == "active",
            "core_online": self.services.get("items", {}).get("neron-core") == "active",
            "llm_online": self.services.get("items", {}).get("neron-llm") == "active",
            "doctor_online": self.services.get("items", {}).get("neron-doctor") == "active",
            "decision_engine": True,
            "memory_online": True,
            "reasoning_online": True,
        }

    def compute_diagnostics(self) -> None:
        self.diagnostics = []

        if self.runtime.get("cpu_usage", 0) >= 90:
            self.diagnostics.append("Charge CPU élevée.")
        if self.runtime.get("ram_usage", 0) >= 90:
            self.diagnostics.append("Utilisation RAM élevée.")
        if self.runtime.get("disk_usage", 0) >= 90:
            self.diagnostics.append("Espace disque critique.")

        for service in ["neron-core", "neron-llm", "neron-doctor", "neron-self-model-loop"]:
            if self.services.get("items", {}).get(service) != "active":
                self.diagnostics.append(f"Le service {service} est inactif.")

        if self.services.get("items", {}).get("neron-cognitive-loop") != "active":
            self.diagnostics.append("La boucle cognitive autonome est inactive.")

    def compute_recommendations(self) -> None:
        self.recommendations = []

        if self.runtime.get("cpu_usage", 0) >= 90:
            self.recommendations.append("Réduire la charge LLM ou basculer vers un modèle plus léger.")
        if self.runtime.get("ram_usage", 0) >= 90:
            self.recommendations.append("Libérer de la mémoire ou réduire les services non essentiels.")
        if self.runtime.get("disk_usage", 0) >= 90:
            self.recommendations.append("Nettoyer les logs, caches ou anciens paquets système.")

        for service in ["neron-core", "neron-llm", "neron-doctor", "neron-self-model-loop"]:
            if self.services.get("items", {}).get(service) != "active":
                self.recommendations.append(f"Redémarrer le service {service}.")

    def refresh(self) -> None:
        self.collect_runtime()
        self._compute_health()
        self.collect_services()
        self.compute_health()
        self.compute_cognitive_state()
        self.compute_diagnostics()
        self.compute_recommendations()
        self.last_update = time.time()

    def _merge_state(self, patch: dict[str, Any]) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

        data = {}

        if STATE_PATH.exists():
            try:
                data = json.loads(
                    STATE_PATH.read_text(encoding="utf-8")
                )
            except Exception:
                data = {}

        for key, value in patch.items():
            if key in ("recent_events", "recent_activity", "intent_history"):
                existing = data.get(key, [])

                if not isinstance(existing, list):
                    existing = []

                if not isinstance(value, list):
                    value = []

                merged = existing + value

                seen = set()
                unique = []

                for item in merged:
                    marker = json.dumps(
                        item,
                        ensure_ascii=False,
                        sort_keys=True,
                    )

                    if marker in seen:
                        continue

                    seen.add(marker)
                    unique.append(item)

                if key == "recent_events":
                    data[key] = unique[-10:]
                elif key == "recent_activity":
                    data[key] = unique[-8:]
                else:
                    data[key] = unique[-5:]

            else:
                data[key] = value

        tmp = STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(STATE_PATH)

    def set_last_intent(self, intent: str, confidence: Any = None) -> None:
        data = load_self_model_state()
        event_count = int(data.get("event_count", 0)) + 1

        entry = {
            "intent": intent,
            "confidence": confidence,
            "timestamp": time.time(),
        }

        self._merge_state({
            "last_intent": entry,
            "intent_history": [entry],
            "event_count": event_count,
        })

    def set_last_agent(self, agent: str | None) -> None:
        self._merge_state({
            "last_agent": {
                "agent": agent,
                "timestamp": time.time(),
            }
        })

    def set_last_error(self, error: str | None) -> None:
        self._merge_state({
            "last_error": {
                "error": error,
                "timestamp": time.time(),
            }
        })

    def set_agents_available(self, agents: Any) -> None:
        try:
            value = list(agents)
        except Exception:
            value = []
        self._merge_state({"agents_available": value})

    def set_last_action(self, action: str | None) -> None:
        self._merge_state({"last_action": {"action": action, "timestamp": time.time()}})

    def set_last_decision(self, decision: str | None) -> None:
        self._merge_state({"last_decision": {"decision": decision, "timestamp": time.time()}})

    def set_last_reasoning(self, reasoning: str | None) -> None:
        self._merge_state({"last_reasoning": {"reasoning": reasoning, "timestamp": time.time()}})

    def add_recent_activity(self, activity: str) -> None:
        data = load_self_model_state()
        activities = data.get("recent_activity", [])
        if not isinstance(activities, list):
            activities = []

        activity = activity.replace("Intent.SELF_STATUS", "self_status")
        activity = activity.replace("Intent.SYSTEM_STATUS", "system_status")

        activities.append({"activity": activity, "timestamp": time.time()})
        self._merge_state({"recent_activity": activities[-8:]})

    def compute_stability_score(self) -> float:
        score = 100.0
        cpu = self.runtime.get("cpu_usage", 0) or 0
        ram = self.runtime.get("ram_usage", 0) or 0
        disk = self.runtime.get("disk_usage", 0) or 0

        if cpu >= 90:
            score -= 20
        elif cpu >= 70:
            score -= 10

        if ram >= 90:
            score -= 20
        elif ram >= 70:
            score -= 10

        if disk >= 90:
            score -= 20
        elif disk >= 85:
            score -= 10

        score -= min(len(self.diagnostics) * 10, 30)
        return max(0.0, round(score, 1))

    def update_cognitive_snapshot(self) -> None:
        cpu = self.runtime.get("cpu_usage", 0) or 0
        ram = self.runtime.get("ram_usage", 0) or 0

        if cpu >= 85 or ram >= 85:
            load = "élevée"
        elif cpu >= 50 or ram >= 60:
            load = "modérée"
        else:
            load = "faible"

        mental = "diagnostic" if self.diagnostics else "monitoring"

        self._merge_state({
            "cognitive_load": load,
            "mental_state": mental,
            "stability_score": self.compute_stability_score(),
        })

    def _format_duration(self, seconds: float | int | None) -> str:
        if seconds is None:
            return "inconnu"
        try:
            seconds = int(seconds)
        except Exception:
            return "inconnu"

        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)

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

    def _compute_health(self) -> None:
        runtime = getattr(self, "runtime", {}) or {}

        cpu = runtime.get("cpu_usage", 0) or 0
        ram = runtime.get("ram_usage", 0) or 0
        disk = runtime.get("disk_usage", 0) or 0

        if cpu >= 90 or ram >= 90 or disk >= 90:
            realtime = "critical"
        elif cpu >= 75 or ram >= 80 or disk >= 85:
            realtime = "warning"
        else:
            realtime = "stable"

        self.health_realtime = realtime

        if self.health_historical in {None, "unknown"}:
            self.health_historical = "stable"

        if realtime == "critical":
            self.health_global = "critical"
        elif realtime == "warning":
            self.health_global = "stable_with_warning"
        else:
            self.health_global = "stable"

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
        }

    def save_state(self) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

        existing = {}
        if STATE_PATH.exists():
            try:
                existing = json.loads(STATE_PATH.read_text(encoding="utf-8"))
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
            "last_action",
            "last_decision",
            "last_reasoning",
            "recent_activity",
            "cognitive_load",
            "mental_state",
            "stability_score",
        ):
            if key in existing and data.get(key) in (None, [], {}, 0):
                data[key] = existing[key]

        tmp = STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(STATE_PATH)

    def summary(self) -> str:
        data = load_self_model_state()
        runtime = data.get("runtime", {})
        cognitive = data.get("cognitive_state", {})
        services = data.get("services", {})
        diagnostics = data.get("diagnostics", [])
        recommendations = data.get("recommendations", [])
        last_intent = data.get("last_intent", {})
        last_agent = data.get("last_agent", {})
        last_error = data.get("last_error", {})
        agents = data.get("agents_available", [])
        intent_history = data.get("intent_history", [])
        recent_activity = data.get("recent_activity", [])
        recent_events = data.get("recent_events", [])

        try:
            from core.world_model.world_model import load_world_model_state
            world = load_world_model_state()
        except Exception:
            world = {}

        health_global = data.get("health_global", "unknown")
        health_realtime = data.get("health_realtime", "unknown")
        health_historical = data.get("health_historical", "unknown")

        uptime = runtime.get("uptime")
        uptime_text = self._format_duration(uptime)
        state_age = self._state_age_text(data.get("last_update"))

        cpu = runtime.get("cpu_usage")
        ram = runtime.get("ram_usage")
        disk = runtime.get("disk_usage")

        loop_state = "active" if cognitive.get("autonomous_loop") else "inactive"

        history_text = "aucun"
        if isinstance(intent_history, list) and intent_history:
            items = []
            for item in intent_history[-5:]:
                if isinstance(item, dict):
                    items.append(f"{item.get('intent')} ({item.get('confidence')})")
            history_text = ", ".join(items) if items else "aucun"

        activity_text = "aucune"
        if isinstance(recent_activity, list) and recent_activity:
            lines = []
            for item in recent_activity[-5:]:
                if isinstance(item, dict):
                    lines.append(f"  • {item.get('activity')}")
            activity_text = "\n".join(lines) if lines else "aucune"

        events_text = "aucun"
        if isinstance(recent_events, list) and recent_events:
            lines = []
            for item in recent_events[-5:]:
                if isinstance(item, dict):
                    lines.append(
                        f"  • {item.get('type')} depuis {item.get('source')}"
                    )
            events_text = "\n".join(lines) if lines else "aucun"

        active_services = [name for name, status in services.items() if status == "active"]
        services_text = ", ".join(active_services) if active_services else "aucun"

        diagnostics_text = "\n".join(f"  • {d}" for d in diagnostics) if diagnostics else "aucun"
        recommendations_text = "\n".join(f"  • {r}" for r in recommendations) if recommendations else "aucune"

        last_intent_name = last_intent.get("intent") if isinstance(last_intent, dict) else None
        last_agent_name = last_agent.get("agent") if isinstance(last_agent, dict) else None
        last_error_text = (last_error.get("error") if isinstance(last_error, dict) else None) or "aucune"

        last_action = data.get("last_action", {})
        last_decision = data.get("last_decision", {})
        last_reasoning = data.get("last_reasoning", {})

        try:
            from core.goals.goal_manager import get_goal_manager

            active_goal = get_goal_manager().get_active_goal()
        except Exception:
            active_goal = None

        active_goal_title = (
            active_goal.get("title")
            if isinstance(active_goal, dict)
            else data.get("active_goal", self.active_goal)
        )

        last_action_text = last_action.get("action") if isinstance(last_action, dict) else None
        last_decision_text = last_decision.get("decision") if isinstance(last_decision, dict) else None
        last_reasoning_text = last_reasoning.get("reasoning") if isinstance(last_reasoning, dict) else None

        world_services = world.get("external_services", {})
        world_network = world.get("network", {})

        world_internet = (
            "accessible"
            if world_network.get("default_gateway_reachable")
            else "indisponible"
        )

        world_dns = (
            "fonctionnel"
            if world_network.get("dns_reachable")
            else "indisponible"
        )

        def _world_service_status(name: str) -> str:
            state = world_services.get(name, {})
            return "actif" if state.get("reachable") else "indisponible"

        summary_line = (
            f"Néron est {health_global}. "
            f"CPU {cpu}%, RAM {ram}%, disque {disk}%. "
            f"Boucle cognitive {loop_state}. "
            f"Environnement {world.get('environment_status', 'unknown')}."
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
- Watchdog : 🟢 Excellent ({data.get("stability_score", 100.0)}/100)
- Boucle cognitive : {loop_state}
- Dernière intention : {last_intent_name}
- Historique intents : {history_text}
- Compteur événements : {data.get("event_count", 0)}
- État : {state_age}
- Dernier agent : {last_agent_name}
- Agents disponibles : {", ".join(agents) if agents else "aucun"}
- Services actifs : {services_text}
- Diagnostics : {diagnostics_text}
- Recommandations : {recommendations_text}
- Dernière erreur : {last_error_text}

Monde externe :
- Environnement : {world.get("environment_status", "unknown")}
- Internet : {world_internet}
- DNS : {world_dns}
- Home Assistant : {_world_service_status("home_assistant")}
- Ollama : {_world_service_status("ollama")}
- Néron LLM API : {_world_service_status("neron_llm_api")}
- Néron Core API : {_world_service_status("neron_core_api")}

Mémoire cognitive :
- Objectif actif : {active_goal_title}
- Dernière action : {last_action_text or "aucune"}
- Dernière décision : {last_decision_text or "aucune"}
- Dernier raisonnement : {last_reasoning_text or "aucun"}
- Activité récente :
{activity_text}
- Événements récents :
{events_text}
- Charge cognitive : {data.get("cognitive_load", "inconnue")}
- État mental : {data.get("mental_state", "inconnu")}
- Score de stabilité : {data.get("stability_score", "inconnu")}/100"""


def load_self_model_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

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
