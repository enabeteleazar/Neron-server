"""Health Center snapshot production."""

from __future__ import annotations

import asyncio
import inspect
import os
import time
from datetime import datetime, timezone
from typing import Any

try:
    import psutil
except ModuleNotFoundError:  # pragma: no cover - exercised in minimal CI images
    psutil = None

from .diagnostics import build_diagnostics, build_recommendations, status_from_diagnostics
from .events import HealthEventBus
from .history import HealthHistory


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def collect_resources() -> dict[str, Any]:
    if psutil is None:
        return {
            "cpu_pct": 0.0,
            "ram_pct": 0.0,
            "ram_used_mb": 0,
            "disk_pct": 0.0,
            "process_ram_mb": 0,
            "uptime_s": round(time.monotonic()),
            "collector": "stdlib_fallback",
        }
    proc = psutil.Process(os.getpid())
    boot_time = getattr(psutil, "boot_time", lambda: time.time())()
    return {
        "cpu_pct": psutil.cpu_percent(interval=0.0),
        "ram_pct": psutil.virtual_memory().percent,
        "ram_used_mb": round(psutil.virtual_memory().used / 1024 / 1024),
        "disk_pct": psutil.disk_usage("/").percent,
        "process_ram_mb": round(proc.memory_info().rss / 1024 / 1024),
        "uptime_s": max(0, round(time.time() - boot_time)),
    }


async def _check_agent(name: str, agent: Any, critical: bool = True) -> dict[str, Any]:
    if agent is None:
        return {"status": "unknown", "critical": critical, "detail": "agent not registered"}
    checker = getattr(agent, "check_connection", None)
    if not checker:
        return {"status": "unknown", "critical": critical, "detail": "no check_connection"}
    try:
        result = checker()
        if inspect.isawaitable(result):
            result = await result
        return {"status": "ok" if result else "unreachable", "critical": critical, "detail": "check_connection"}
    except Exception as exc:
        return {"status": "unreachable", "critical": critical, "detail": str(exc)}


async def collect_services(agents: dict[str, Any] | None = None) -> dict[str, Any]:
    agents = agents or {}
    critical_services = {
        "llm": agents.get("llm") or agents.get("llm_agent"),
        "stt": agents.get("stt") or agents.get("stt_agent"),
        "tts": agents.get("tts") or agents.get("tts_agent"),
        "memory": agents.get("memory") or agents.get("memory_agent"),
    }
    checks = [_check_agent(name, agent, critical=(name != "memory")) for name, agent in critical_services.items()]
    results = await asyncio.gather(*checks)
    return dict(zip(critical_services.keys(), results))


class HealthCenter:
    def __init__(self, event_bus: HealthEventBus | None = None, history: HealthHistory | None = None):
        self.event_bus = event_bus or HealthEventBus()
        self.history = history or HealthHistory()
        self.agents: dict[str, Any] = {}
        self._service_states: dict[str, str] = {}

    def configure(self, agents: dict[str, Any] | None = None) -> None:
        self.agents = agents or {}

    def ingest_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return self.event_bus.ingest(event)

    async def create_snapshot(self) -> dict[str, Any]:
        resources = collect_resources()
        services = await collect_services(self.agents)
        recent_events = self.event_bus.recent(limit=20, relevant_only=True)
        base_snapshot = {
            "status": "stable",
            "services": services,
            "resources": resources,
            "diagnostics": [],
            "recommendations": [],
            "events": recent_events,
            "timestamp": utc_now_iso(),
        }
        diagnostics = build_diagnostics(base_snapshot, recent_events)
        recommendations = build_recommendations(diagnostics)
        snapshot = {**base_snapshot, "diagnostics": diagnostics, "recommendations": recommendations}
        snapshot["status"] = status_from_diagnostics(diagnostics)

        previous_status, current_status = self.history.add_snapshot(snapshot)
        self.event_bus.publish("health.snapshot.created", {"status": current_status, "timestamp": snapshot["timestamp"]})
        if previous_status is not None and previous_status != current_status:
            self.event_bus.publish("health.status.changed", {"previous": previous_status, "current": current_status})
        self._publish_service_transitions(services)
        self._publish_resource_events(resources)
        if diagnostics:
            self.event_bus.publish("health.diagnostic.created", {"count": len(diagnostics), "status": current_status})
        return snapshot

    def _publish_service_transitions(self, services: dict[str, Any]) -> None:
        for name, service in services.items():
            current = service.get("status", "unknown")
            previous = self._service_states.get(name)
            if current == "unreachable" and previous != "unreachable":
                self.event_bus.publish("health.service.unreachable", {"service": name, "detail": service.get("detail")})
            elif current in {"ok", "healthy"} and previous == "unreachable":
                self.event_bus.publish("health.service.recovered", {"service": name})
            self._service_states[name] = current

    def _publish_resource_events(self, resources: dict[str, Any]) -> None:
        for key, warning, critical in (("cpu_pct", 80, 95), ("ram_pct", 85, 95), ("disk_pct", 90, 97)):
            value = resources.get(key)
            try:
                value_float = float(value)
            except (TypeError, ValueError):
                continue
            if value_float >= critical:
                self.event_bus.publish("health.resource.critical", {"resource": key, "value": value_float})
            elif value_float >= warning:
                self.event_bus.publish("health.resource.warning", {"resource": key, "value": value_float})


health_center = HealthCenter()
