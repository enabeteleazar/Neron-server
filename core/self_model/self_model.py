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
import asyncio

from core.events.event import Event
from core.events.event_bus import event_bus
from core.events import event_types
from core.identity import get_identity


STATE_PATH = Path("/etc/neron/data/self_model_state.json")
ACTION_HISTORY_PATH = Path("/etc/neron/data/action_history.jsonl")


@dataclass
class SelfModel:
    identity: dict[str, Any] = field(default_factory=dict)
    runtime: dict[str, Any] = field(default_factory=dict)
    runtime_trend: dict[str, Any] = field(default_factory=dict)
    long_term_state_memory: dict[str, Any] = field(default_factory=dict)
    self_confidence: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    performance_self_evaluation: dict[str, Any] = field(default_factory=dict)
    services: dict[str, str] = field(default_factory=dict)
    cognitive_state: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    code_awareness: dict[str, Any] = field(default_factory=dict)

    active_goal: str = "maintenir la stabilité système"
    health_realtime: str = "unknown"
    health_historical: str = "unknown"
    health_global: str = "unknown"
    last_update: float | None = None

    def __post_init__(self) -> None:
        self.identity = get_identity()

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

    def compute_runtime_trend(self) -> None:
        history_limit = 10
        now = time.time()

        existing = {}

        if STATE_PATH.exists():
            try:
                existing = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        history = existing.get("runtime_history", [])

        if not isinstance(history, list):
            history = []

        sample = {
            "timestamp": now,
            "cpu_usage": self.runtime.get("cpu_usage"),
            "ram_usage": self.runtime.get("ram_usage"),
            "disk_usage": self.runtime.get("disk_usage"),
            "swap_usage": self.runtime.get("swap_usage"),
            "health_realtime": self.health_realtime,
        }

        history.append(sample)
        history = history[-history_limit:]

        def _avg(key: str) -> float:
            values = [
                item.get(key)
                for item in history
                if isinstance(item.get(key), (int, float))
            ]

            if not values:
                return 0.0

            return round(sum(values) / len(values), 2)

        cpu_spikes = sum(
            1
            for item in history
            if (item.get("cpu_usage") or 0) >= 90
        )

        ram_spikes = sum(
            1
            for item in history
            if (item.get("ram_usage") or 0) >= 90
        )

        high_pressure_samples = sum(
            1
            for item in history
            if (
                (item.get("cpu_usage") or 0) >= 90
                or (item.get("ram_usage") or 0) >= 90
                or (item.get("disk_usage") or 0) >= 90
            )
        )

        if high_pressure_samples >= 5:
            stability = "unstable"
        elif high_pressure_samples >= 2:
            stability = "variable"
        else:
            stability = "stable"

        self.runtime_trend = {
            "samples": len(history),
            "cpu_avg": _avg("cpu_usage"),
            "ram_avg": _avg("ram_usage"),
            "disk_avg": _avg("disk_usage"),
            "swap_avg": _avg("swap_usage"),
            "cpu_spikes": cpu_spikes,
            "ram_spikes": ram_spikes,
            "high_pressure_samples": high_pressure_samples,
            "stability": stability,
            "history_limit": history_limit,
        }

        self._merge_state(
            {
                "runtime_history": history,
                "runtime_trend": self.runtime_trend,
            }
        )


    def collect_services(self) -> None:
        critical = [
            "neron-core",
            "neron-llm",
            "neron-doctor",
            "neron-cognitive-loop",
            "neron-self-model-loop",
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
        services = self.services.get("items", {}) or {}
        service_summary = self.services.get("summary", {}) or {}

        cpu = self.runtime.get("cpu_usage", 0) or 0
        ram = self.runtime.get("ram_usage", 0) or 0
        disk = self.runtime.get("disk_usage", 0) or 0
        swap = self.runtime.get("swap_usage", 0) or 0

        self_model_loop = services.get("neron-self-model-loop") == "active"
        autonomous_loop = services.get("neron-cognitive-loop") == "active"
        core_online = services.get("neron-core") == "active"
        llm_online = services.get("neron-llm") == "active"
        doctor_online = services.get("neron-doctor") == "active"

        critical_services_ok = bool(service_summary.get("all_critical_active", False))

        runtime_pressure = "normal"
        primary_issue = None
        severity_score = 0

        if cpu >= 90:
            runtime_pressure = "high"
            primary_issue = "cpu_overload"
            severity_score = max(severity_score, 70)
        elif cpu >= 75:
            runtime_pressure = "moderate"
            primary_issue = "cpu_pressure"
            severity_score = max(severity_score, 45)

        if ram >= 90:
            runtime_pressure = "high"
            primary_issue = primary_issue or "ram_overload"
            severity_score = max(severity_score, 75)
        elif ram >= 80:
            runtime_pressure = "moderate"
            primary_issue = primary_issue or "ram_pressure"
            severity_score = max(severity_score, 45)

        if disk >= 90:
            runtime_pressure = "high"
            primary_issue = primary_issue or "disk_pressure"
            severity_score = max(severity_score, 80)

        if swap >= 50:
            runtime_pressure = "moderate"
            primary_issue = primary_issue or "swap_usage_high"
            severity_score = max(severity_score, 50)

        if not critical_services_ok:
            primary_issue = "critical_service_down"
            severity_score = max(severity_score, 85)

        autonomy_available = (
            self_model_loop
            and autonomous_loop
            and core_online
            and llm_online
            and doctor_online
            and critical_services_ok
        )

        degraded_mode = not autonomy_available or severity_score >= 70

        if severity_score >= 85:
            state = "critical"
        elif severity_score >= 70:
            state = "degraded"
        elif severity_score >= 45:
            state = "warning"
        else:
            state = "stable"

        self.cognitive_state = {
            "state": state,
            "severity_score": severity_score,
            "primary_issue": primary_issue,
            "runtime_pressure": runtime_pressure,
            "autonomy_available": autonomy_available,
            "degraded_mode": degraded_mode,
            "critical_services_ok": critical_services_ok,
            "self_model_loop": self_model_loop,
            "autonomous_loop": autonomous_loop,
            "core_online": core_online,
            "llm_online": llm_online,
            "doctor_online": doctor_online,
            "decision_engine": True,
            "memory_online": True,
            "reasoning_online": True,
        }

    def compute_runtime_mode(self) -> None:
        cognitive_state = self.cognitive_state or {}

        state = cognitive_state.get("state", "stable")
        severity_score = cognitive_state.get("severity_score", 0) or 0
        runtime_pressure = cognitive_state.get("runtime_pressure", "normal")
        autonomy_available = cognitive_state.get("autonomy_available", False)

        if state == "critical" or severity_score >= 85 or not autonomy_available:
            runtime_mode = "survival"
            planner_enabled = False
            heavy_reasoning_allowed = False
            autonomous_actions_allowed = False
            max_parallel_agents = 1

        elif state == "degraded" or severity_score >= 70 or runtime_pressure == "high":
            runtime_mode = "degraded"
            planner_enabled = True
            heavy_reasoning_allowed = False
            autonomous_actions_allowed = True
            max_parallel_agents = 1

        elif state == "warning" or severity_score >= 45 or runtime_pressure == "moderate":
            runtime_mode = "prudent"
            planner_enabled = True
            heavy_reasoning_allowed = False
            autonomous_actions_allowed = True
            max_parallel_agents = 1

        else:
            runtime_mode = "normal"
            planner_enabled = True
            heavy_reasoning_allowed = True
            autonomous_actions_allowed = True
            max_parallel_agents = 3

        self.cognitive_state["runtime_mode"] = runtime_mode
        self.cognitive_state["planner_enabled"] = planner_enabled
        self.cognitive_state["heavy_reasoning_allowed"] = heavy_reasoning_allowed
        self.cognitive_state["autonomous_actions_allowed"] = autonomous_actions_allowed
        self.cognitive_state["max_parallel_agents"] = max_parallel_agents


    def compute_probable_cause(self) -> None:
        existing = {}

        if STATE_PATH.exists():
            try:
                existing = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        recent_events = existing.get("recent_events", [])
        if not isinstance(recent_events, list):
            recent_events = []

        recent_activity = existing.get("recent_activity", [])
        if not isinstance(recent_activity, list):
            recent_activity = []

        primary_issue = self.cognitive_state.get("primary_issue")
        runtime_pressure = self.cognitive_state.get("runtime_pressure")
        cpu = self.runtime.get("cpu_usage", 0) or 0
        ram = self.runtime.get("ram_usage", 0) or 0
        swap = self.runtime.get("swap_usage", 0) or 0

        evidence: list[str] = []
        probable_cause = None

        recent_types = [
            event.get("type")
            for event in recent_events[-5:]
            if isinstance(event, dict)
        ]

        recent_sources = [
            event.get("source")
            for event in recent_events[-5:]
            if isinstance(event, dict)
        ]

        recent_activity_text = " ".join(
            str(item.get("activity", ""))
            for item in recent_activity[-5:]
            if isinstance(item, dict)
        ).lower()

        if cpu >= 90:
            evidence.append("cpu_usage >= 90")

        if ram >= 90:
            evidence.append("ram_usage >= 90")

        if swap >= 50:
            evidence.append("swap_usage >= 50")

        if runtime_pressure:
            evidence.append(f"runtime_pressure = {runtime_pressure}")

        if "system.alert" in recent_types:
            evidence.append("recent system.alert detected")

        if "self.monitor" in recent_sources:
            evidence.append("alert source = self.monitor")

        if primary_issue in {"cpu_overload", "cpu_pressure"}:
            if "stt" in recent_activity_text or "vocal" in recent_activity_text:
                probable_cause = "voice_pipeline_cpu_pressure"
                evidence.append("recent activity mentions stt/vocal")
            elif "llm" in recent_activity_text or "agent" in recent_activity_text:
                probable_cause = "agent_or_llm_runtime_pressure"
                evidence.append("recent activity mentions llm/agent")
            elif "system.alert" in recent_types:
                probable_cause = "runtime_cpu_pressure"
            else:
                probable_cause = "cpu_pressure_unknown_origin"

        elif primary_issue in {"ram_overload", "ram_pressure"}:
            probable_cause = "memory_pressure"
        elif primary_issue == "swap_usage_high":
            probable_cause = "memory_swap_pressure"
        elif primary_issue == "critical_service_down":
            probable_cause = "critical_service_unavailable"
        elif primary_issue == "disk_pressure":
            probable_cause = "storage_pressure"

        self.cognitive_state["probable_cause"] = probable_cause
        self.cognitive_state["evidence"] = evidence[-10:]


    def compute_long_term_state_memory(self) -> None:
        existing = {}

        if STATE_PATH.exists():
            try:
                existing = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        memory = existing.get("long_term_state_memory", {})
        if not isinstance(memory, dict):
            memory = {}

        state_history = existing.get("state_history", [])
        if not isinstance(state_history, list):
            state_history = []

        runtime_mode_history = existing.get("runtime_mode_history", [])
        if not isinstance(runtime_mode_history, list):
            runtime_mode_history = []

        state_counts = memory.get("state_counts", {})
        if not isinstance(state_counts, dict):
            state_counts = {}

        runtime_mode_counts = memory.get("runtime_mode_counts", {})
        if not isinstance(runtime_mode_counts, dict):
            runtime_mode_counts = {}

        last_seen_transition_ts = memory.get("last_seen_transition_ts", 0) or 0
        last_seen_runtime_mode_transition_ts = memory.get("last_seen_runtime_mode_transition_ts", 0) or 0

        new_state_transitions = [
            item for item in state_history
            if isinstance(item, dict)
            and (item.get("timestamp") or 0) > last_seen_transition_ts
        ]

        new_runtime_mode_transitions = [
            item for item in runtime_mode_history
            if isinstance(item, dict)
            and (item.get("timestamp") or 0) > last_seen_runtime_mode_transition_ts
        ]

        for item in new_state_transitions:
            to_state = item.get("to") or "unknown"
            state_counts[to_state] = int(state_counts.get(to_state, 0)) + 1
            last_seen_transition_ts = max(
                last_seen_transition_ts,
                item.get("timestamp") or 0,
            )

        for item in new_runtime_mode_transitions:
            to_mode = item.get("to") or "unknown"
            runtime_mode_counts[to_mode] = int(runtime_mode_counts.get(to_mode, 0)) + 1
            last_seen_runtime_mode_transition_ts = max(
                last_seen_runtime_mode_transition_ts,
                item.get("timestamp") or 0,
            )

        total_transitions = sum(int(v) for v in state_counts.values())
        total_runtime_mode_transitions = sum(int(v) for v in runtime_mode_counts.values())

        dominant_state = max(
            state_counts,
            key=state_counts.get,
        ) if state_counts else self.cognitive_state.get("state", "unknown")

        dominant_runtime_mode = max(
            runtime_mode_counts,
            key=runtime_mode_counts.get,
        ) if runtime_mode_counts else self.cognitive_state.get("runtime_mode", "unknown")

        unstable_states = (
            int(state_counts.get("warning", 0))
            + int(state_counts.get("degraded", 0)) * 2
            + int(state_counts.get("critical", 0)) * 3
        )

        instability_score = 0
        if total_transitions > 0:
            instability_score = round(
                min(100, (unstable_states / total_transitions) * 100),
                2,
            )

        self.long_term_state_memory = {
            "total_transitions": total_transitions,
            "total_runtime_mode_transitions": total_runtime_mode_transitions,
            "state_counts": state_counts,
            "runtime_mode_counts": runtime_mode_counts,
            "dominant_state": dominant_state,
            "dominant_runtime_mode": dominant_runtime_mode,
            "instability_score": instability_score,
            "last_seen_transition_ts": last_seen_transition_ts,
            "last_seen_runtime_mode_transition_ts": last_seen_runtime_mode_transition_ts,
        }

        self._merge_state({
            "long_term_state_memory": self.long_term_state_memory,
        })


    def compute_temporal_state(self) -> None:
        now = time.time()

        existing = {}
        if STATE_PATH.exists():
            try:
                existing = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        previous_state = existing.get("current_state")
        previous_runtime_mode = existing.get("current_runtime_mode")

        current_state = self.cognitive_state.get("state")
        current_runtime_mode = self.cognitive_state.get("runtime_mode")

        state_started_at = existing.get("state_started_at")
        runtime_mode_started_at = existing.get("runtime_mode_started_at")

        state_history = existing.get("state_history", [])
        if not isinstance(state_history, list):
            state_history = []

        runtime_mode_history = existing.get("runtime_mode_history", [])
        if not isinstance(runtime_mode_history, list):
            runtime_mode_history = []

        if previous_state != current_state or not state_started_at:
            if previous_state is not None and previous_state != current_state:
                previous_duration = round(now - float(state_started_at), 2) if state_started_at else 0
                force_publish = current_state == "critical"

                if previous_duration >= 30 or force_publish:
                    state_history.append({
                        "timestamp": now,
                        "from": previous_state,
                        "to": current_state,
                        "previous_duration_seconds": previous_duration,
                        "primary_issue": self.cognitive_state.get("primary_issue"),
                        "probable_cause": self.cognitive_state.get("probable_cause"),
                        "evidence": self.cognitive_state.get("evidence", []),
                        "severity_score": self.cognitive_state.get("severity_score"),
                        "force_publish": force_publish,
                    })
            state_started_at = now

        if previous_runtime_mode != current_runtime_mode or not runtime_mode_started_at:
            if previous_runtime_mode is not None and previous_runtime_mode != current_runtime_mode:
                previous_duration = round(now - float(runtime_mode_started_at), 2) if runtime_mode_started_at else 0
                force_publish = current_runtime_mode == "survival"

                if previous_duration >= 30 or force_publish:
                    runtime_mode_history.append({
                        "timestamp": now,
                        "from": previous_runtime_mode,
                        "to": current_runtime_mode,
                        "previous_duration_seconds": previous_duration,
                        "primary_issue": self.cognitive_state.get("primary_issue"),
                        "probable_cause": self.cognitive_state.get("probable_cause"),
                        "evidence": self.cognitive_state.get("evidence", []),
                        "severity_score": self.cognitive_state.get("severity_score"),
                        "force_publish": force_publish,
                    })
            runtime_mode_started_at = now

        state_history = state_history[-20:]
        runtime_mode_history = runtime_mode_history[-20:]

        self.cognitive_state["previous_state"] = previous_state
        self.cognitive_state["previous_runtime_mode"] = previous_runtime_mode
        self.cognitive_state["state_history"] = state_history
        self.cognitive_state["runtime_mode_history"] = runtime_mode_history
        self.cognitive_state["state_started_at"] = state_started_at
        self.cognitive_state["runtime_mode_started_at"] = runtime_mode_started_at
        self.cognitive_state["state_duration_seconds"] = round(now - float(state_started_at), 2)
        self.cognitive_state["runtime_mode_duration_seconds"] = round(now - float(runtime_mode_started_at), 2)

        self._merge_state(
            {
                "current_state": current_state,
                "current_runtime_mode": current_runtime_mode,
                "state_started_at": state_started_at,
                "runtime_mode_started_at": runtime_mode_started_at,
                "state_history": state_history,
                "runtime_mode_history": runtime_mode_history,
            }
        )


    def compute_capabilities(self) -> None:
        services = self.services.get("items", {}) or {}
        service_summary = self.services.get("summary", {}) or {}
        agents_available = []

        existing = {}
        if STATE_PATH.exists():
            try:
                existing = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        raw_agents = existing.get("agents_available", [])
        if isinstance(raw_agents, list):
            agents_available = raw_agents

        capability_map = {
            "core_api": services.get("neron-core") == "active",
            "llm": services.get("neron-llm") == "active",
            "doctor": services.get("neron-doctor") == "active",
            "cognitive_loop": services.get("neron-cognitive-loop") == "active",
            "self_model_loop": services.get("neron-self-model-loop") == "active",
            "homeassistant": services.get("neron-homeassistant") == "active",
            "kula": services.get("neron-kula") == "active",
            "voice_input": services.get("neron-stt") == "active",
            "voice_output": services.get("neron-vocal") == "active",
            "memory": True,
            "planner": True,
            "governor": True,
            "event_bus": True,
            "code_agent": "code_agent" in agents_available or True,
            "self_repair": True,
        }

        available = [
            name for name, enabled in capability_map.items()
            if enabled is True
        ]
        unavailable = [
            name for name, enabled in capability_map.items()
            if enabled is not True
        ]

        critical_ok = bool(service_summary.get("all_critical_active", False))
        autonomy_available = self.cognitive_state.get("autonomy_available", False)
        runtime_mode = self.cognitive_state.get("runtime_mode", "unknown")

        if not critical_ok:
            autonomy_level = "unavailable"
        elif runtime_mode == "survival":
            autonomy_level = "minimal"
        elif runtime_mode in {"prudent", "degraded"}:
            autonomy_level = "partial"
        elif autonomy_available:
            autonomy_level = "operational"
        else:
            autonomy_level = "partial"

        self.capabilities = {
            "items": capability_map,
            "available": available,
            "unavailable": unavailable,
            "available_count": len(available),
            "unavailable_count": len(unavailable),
            "autonomy_level": autonomy_level,
            "agents_available": agents_available,
        }

        self._merge_state({
            "capabilities": self.capabilities,
        })


    def compute_performance_self_evaluation(self) -> None:
        recent_actions: list[dict[str, Any]] = []

        if ACTION_HISTORY_PATH.exists():
            try:
                lines = ACTION_HISTORY_PATH.read_text(
                    encoding="utf-8"
                ).splitlines()[-50:]

                for line in lines:
                    try:
                        item = json.loads(line)
                    except Exception:
                        continue

                    if isinstance(item, dict):
                        recent_actions.append(item)
            except Exception:
                recent_actions = []

        total = len(recent_actions)
        success = sum(1 for item in recent_actions if item.get("status") == "success")
        blocked = sum(1 for item in recent_actions if item.get("status") == "blocked")
        noop = sum(1 for item in recent_actions if item.get("status") == "noop")
        failed = sum(1 for item in recent_actions if item.get("status") == "failed")

        success_rate = round((success / total) * 100, 2) if total else 0.0

        runtime_stability = (self.runtime_trend or {}).get("stability", "unknown")
        confidence_level = (self.self_confidence or {}).get("level", "unknown")
        instability_score = (self.long_term_state_memory or {}).get("instability_score", 0) or 0

        score = 100
        notes: list[str] = []

        if total == 0:
            score -= 20
            notes.append("Aucune action récente disponible pour évaluer la performance.")

        if success_rate < 50 and total > 0:
            score -= 30
            notes.append("Taux de succès récent faible.")
        elif success_rate < 80 and total > 0:
            score -= 15
            notes.append("Taux de succès récent perfectible.")

        if blocked > 0:
            score -= min(20, blocked * 5)
            notes.append("Certaines actions ont été bloquées par la policy runtime.")

        if failed > 0:
            score -= min(30, failed * 10)
            notes.append("Des actions récentes ont échoué.")

        if runtime_stability == "unstable":
            score -= 20
            notes.append("Runtime instable.")
        elif runtime_stability == "variable":
            score -= 10
            notes.append("Runtime variable.")

        if confidence_level == "low":
            score -= 15
            notes.append("Confiance interne faible.")
        elif confidence_level == "medium":
            score -= 5
            notes.append("Confiance interne moyenne.")

        if instability_score >= 80:
            score -= 10
            notes.append("Historique long terme instable.")

        score = max(0, min(100, score))

        if score >= 80:
            level = "good"
        elif score >= 50:
            level = "medium"
        else:
            level = "poor"

        if not notes:
            notes.append("Performance récente cohérente.")

        self.performance_self_evaluation = {
            "score": score,
            "level": level,
            "actions_total_recent": total,
            "actions_success": success,
            "actions_blocked": blocked,
            "actions_noop": noop,
            "actions_failed": failed,
            "success_rate": success_rate,
            "runtime_stability": runtime_stability,
            "confidence_level": confidence_level,
            "notes": notes,
            "updated_at": time.time(),
        }

        self._merge_state({
            "performance_self_evaluation": self.performance_self_evaluation,
        })


    def compute_self_confidence(self) -> None:
        score = 100
        reasons: list[str] = []

        cognitive_state = self.cognitive_state or {}
        runtime_trend = self.runtime_trend or {}
        long_term = self.long_term_state_memory or {}

        runtime_pressure = cognitive_state.get("runtime_pressure")
        probable_cause = cognitive_state.get("probable_cause")
        critical_services_ok = cognitive_state.get("critical_services_ok")
        instability_score = long_term.get("instability_score", 0) or 0
        cpu_spikes = runtime_trend.get("cpu_spikes", 0) or 0

        if instability_score >= 80:
            score -= 25
            reasons.append("Instabilité runtime élevée.")
        elif instability_score >= 50:
            score -= 10
            reasons.append("Transitions runtime variables.")

        if runtime_pressure == "high":
            score -= 20
            reasons.append("Pression runtime élevée.")
        elif runtime_pressure == "moderate":
            score -= 10
            reasons.append("Pression runtime modérée.")

        if self.health_realtime == "warning":
            score -= 15
            reasons.append("Santé realtime dégradée.")

        if critical_services_ok is False:
            score -= 30
            reasons.append("Services critiques indisponibles.")

        if probable_cause is None and runtime_pressure in {"moderate", "high"}:
            score -= 10
            reasons.append("Cause probable inconnue malgré une pression runtime.")

        if cpu_spikes >= 5:
            score -= 10
            reasons.append("Pics CPU fréquents.")

        if not reasons:
            reasons.append("État interne cohérent et services critiques disponibles.")

        score = max(0, min(100, score))

        if score >= 80:
            level = "high"
        elif score >= 50:
            level = "medium"
        else:
            level = "low"

        self.self_confidence = {
            "score": score,
            "level": level,
            "reasons": reasons,
            "updated_at": time.time(),
        }

        self._merge_state({
            "self_confidence": self.self_confidence,
        })


    def publish_temporal_events(self) -> None:
        state_history = self.cognitive_state.get("state_history", [])
        runtime_mode_history = self.cognitive_state.get("runtime_mode_history", [])

        events: list[Event] = []

        existing = {}
        if STATE_PATH.exists():
            try:
                existing = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        last_published_state_ts = existing.get("last_published_state_change_ts")
        last_published_mode_ts = existing.get("last_published_runtime_mode_change_ts")

        published_patch = {}

        if state_history:
            last_state_change = state_history[-1]
            state_ts = last_state_change.get("timestamp")

            if (
                state_ts == self.cognitive_state.get("state_started_at")
                and state_ts != last_published_state_ts
            ):
                events.append(Event(
                    type=event_types.SELF_MODEL_STATE_CHANGED,
                    source="self_model",
                    payload=last_state_change,
                ))
                published_patch["last_published_state_change_ts"] = state_ts

        if runtime_mode_history:
            last_mode_change = runtime_mode_history[-1]
            mode_ts = last_mode_change.get("timestamp")

            if (
                mode_ts == self.cognitive_state.get("runtime_mode_started_at")
                and mode_ts != last_published_mode_ts
            ):
                events.append(Event(
                    type=event_types.SELF_MODEL_RUNTIME_MODE_CHANGED,
                    source="self_model",
                    payload=last_mode_change,
                ))
                published_patch["last_published_runtime_mode_change_ts"] = mode_ts

        if published_patch:
            self._merge_state(published_patch)

        if not events:
            return

        async def _publish_all() -> None:
            for event in events:
                await event_bus.publish(event)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_publish_all())
        else:
            loop.create_task(_publish_all())


    def compute_diagnostics(self) -> None:
        self.diagnostics = []

        cognitive_state = self.cognitive_state or {}
        state = cognitive_state.get("state")
        severity_score = cognitive_state.get("severity_score", 0)
        primary_issue = cognitive_state.get("primary_issue")
        runtime_pressure = cognitive_state.get("runtime_pressure")
        autonomy_available = cognitive_state.get("autonomy_available")
        critical_services_ok = cognitive_state.get("critical_services_ok")

        if state in {"warning", "degraded", "critical"}:
            self.diagnostics.append(
                f"État cognitif {state} détecté avec une sévérité de {severity_score}/100."
            )

        if primary_issue == "cpu_overload":
            self.diagnostics.append("Surcharge CPU détectée : la capacité de raisonnement peut être ralentie.")
        elif primary_issue == "cpu_pressure":
            self.diagnostics.append("Pression CPU modérée détectée.")
        elif primary_issue == "ram_overload":
            self.diagnostics.append("Surcharge RAM détectée : risque de ralentissement ou d'échec d'agents.")
        elif primary_issue == "ram_pressure":
            self.diagnostics.append("Pression RAM modérée détectée.")
        elif primary_issue == "disk_pressure":
            self.diagnostics.append("Pression disque détectée : les journaux, caches ou états persistants peuvent être affectés.")
        elif primary_issue == "swap_usage_high":
            self.diagnostics.append("Utilisation importante du swap détectée : performances probablement dégradées.")
        elif primary_issue == "critical_service_down":
            self.diagnostics.append("Un ou plusieurs services critiques sont inactifs.")

        if runtime_pressure == "high":
            self.diagnostics.append("Pression runtime élevée : Néron devrait éviter les tâches lourdes temporairement.")
        elif runtime_pressure == "moderate":
            self.diagnostics.append("Pression runtime modérée : Néron peut fonctionner mais doit rester prudent.")

        if autonomy_available is False:
            self.diagnostics.append("Autonomie cognitive indisponible : au moins une brique critique est inactive.")

        if critical_services_ok is False:
            inactive = self.services.get("summary", {}).get("critical_inactive_services", [])
            self.diagnostics.append(f"Services critiques inactifs : {', '.join(inactive)}.")

    def compute_recommendations(self) -> None:
        self.recommendations = []

        cognitive_state = self.cognitive_state or {}
        primary_issue = cognitive_state.get("primary_issue")
        runtime_pressure = cognitive_state.get("runtime_pressure")
        degraded_mode = cognitive_state.get("degraded_mode")
        autonomy_available = cognitive_state.get("autonomy_available")

        if primary_issue in {"cpu_overload", "cpu_pressure"}:
            self.recommendations.append("Réduire temporairement la charge LLM ou basculer vers un modèle plus léger.")
            self.recommendations.append("Reporter les tâches cognitives non essentielles tant que le CPU reste élevé.")

        if primary_issue in {"ram_overload", "ram_pressure"}:
            self.recommendations.append("Libérer de la mémoire ou réduire les services non essentiels.")

        if primary_issue == "disk_pressure":
            self.recommendations.append("Nettoyer les logs, caches ou anciens paquets système.")

        if primary_issue == "swap_usage_high":
            self.recommendations.append("Limiter les processus gourmands et vérifier la pression mémoire.")

        if primary_issue == "critical_service_down":
            inactive = self.services.get("summary", {}).get("critical_inactive_services", [])
            for service in inactive:
                self.recommendations.append(f"Redémarrer le service critique {service}.")

        if runtime_pressure == "high":
            self.recommendations.append("Activer un mode prudent : limiter planner, critic et appels LLM lourds.")

        if degraded_mode:
            self.recommendations.append("Maintenir Néron en mode dégradé jusqu'au retour d'un état stable.")

        if autonomy_available is False:
            self.recommendations.append("Restaurer les services critiques avant de lancer des actions autonomes.")

    def refresh(self) -> None:
        self.collect_runtime()
        self.collect_code_awareness()
        self._compute_health()
        self.collect_services()
        self.compute_health()
        self.compute_runtime_trend()
        self.compute_cognitive_state()
        self.compute_runtime_mode()
        self.compute_probable_cause()
        self.compute_temporal_state()
        self.compute_long_term_state_memory()
        self.compute_capabilities()
        self.compute_self_confidence()
        self.compute_performance_self_evaluation()
        self.publish_temporal_events()
        self.compute_diagnostics()
        self.compute_recommendations()
        self.last_update = time.time()

    def collect_code_awareness(self) -> None:
        try:
            from core.code_awareness.scanner import scan_project

            scan = scan_project(max_depth=1)
            self.code_awareness = {
                "modules": scan.get("modules", 0),
                "files": scan.get("files", 0),
                "last_scan": time.time(),
                "architecture_known": True,
            }
        except Exception as exc:
            self.code_awareness = {
                "modules": 0,
                "files": 0,
                "last_scan": time.time(),
                "architecture_known": False,
                "error": str(exc),
            }

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
        self.identity = get_identity()
        return {
            "identity": self.identity,
            "runtime": self.runtime,
            "runtime_trend": self.runtime_trend,
            "long_term_state_memory": self.long_term_state_memory,
            "self_confidence": self.self_confidence,
            "capabilities": self.capabilities,
            "performance_self_evaluation": self.performance_self_evaluation,
            "services": self.services,
            "health_realtime": self.health_realtime,
            "health_historical": self.health_historical,
            "health_global": self.health_global,
            "active_goal": self.active_goal,
            "cognitive_state": self.cognitive_state,
            "code_awareness": self.code_awareness,
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

Historique cognitif interne :
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
