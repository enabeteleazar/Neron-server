"""Diagnostic and recommendation generation for Health Center."""

from __future__ import annotations

from typing import Any

WARNING_THRESHOLDS = {"cpu_pct": 80.0, "ram_pct": 85.0, "disk_pct": 90.0}
CRITICAL_THRESHOLDS = {"cpu_pct": 95.0, "ram_pct": 95.0, "disk_pct": 97.0}


def _resource_value(resources: dict[str, Any], key: str) -> float | None:
    value = resources.get(key)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_diagnostics(snapshot: dict[str, Any], recent_events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    resources = snapshot.get("resources", {})
    services = snapshot.get("services", {})
    recent_events = recent_events or []

    for key, threshold in CRITICAL_THRESHOLDS.items():
        value = _resource_value(resources, key)
        if value is not None and value >= threshold:
            diagnostics.append({
                "severity": "critical",
                "code": f"{key}.critical",
                "message": f"{key} critique ({value}%).",
                "source": "health_center.resources",
            })

    for key, threshold in WARNING_THRESHOLDS.items():
        value = _resource_value(resources, key)
        if value is not None and threshold <= value < CRITICAL_THRESHOLDS[key]:
            diagnostics.append({
                "severity": "warning",
                "code": f"{key}.warning",
                "message": f"{key} élevé ({value}%).",
                "source": "health_center.resources",
            })

    for name, service in services.items():
        if service.get("status") not in {"ok", "healthy", "unknown"}:
            diagnostics.append({
                "severity": "critical" if service.get("critical", True) else "warning",
                "code": "service.unreachable",
                "message": f"Service {name} indisponible: {service.get('detail', service.get('status'))}.",
                "source": "health_center.services",
                "service": name,
            })

    for event in recent_events[-10:]:
        event_type = event.get("type")
        if event_type in {"system.service.error", "agent.execution.failed", "llm.provider.error"}:
            diagnostics.append({
                "severity": "warning",
                "code": "recent.event.error",
                "message": f"Événement récent pertinent: {event_type}.",
                "source": "health_center.events",
                "event_type": event_type,
            })

    return diagnostics


def build_recommendations(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for diagnostic in diagnostics:
        code = diagnostic.get("code", "")
        if code.endswith(".critical") or code.endswith(".warning"):
            resource = code.split(".", 1)[0]
            key = f"resource:{resource}"
            if key not in seen:
                recommendations.append({
                    "priority": "high" if diagnostic.get("severity") == "critical" else "medium",
                    "action": f"Réduire ou investiguer l'utilisation {resource}.",
                    "reason": diagnostic.get("message"),
                })
                seen.add(key)
        elif code == "service.unreachable":
            service = diagnostic.get("service", "service")
            key = f"service:{service}"
            if key not in seen:
                recommendations.append({
                    "priority": "high",
                    "action": f"Vérifier {service}; laisser Watchdog relancer si configuré.",
                    "reason": diagnostic.get("message"),
                })
                seen.add(key)
        elif code == "recent.event.error" and "events" not in seen:
            recommendations.append({
                "priority": "medium",
                "action": "Corréler les erreurs récentes avec les services et agents concernés.",
                "reason": diagnostic.get("message"),
            })
            seen.add("events")
    return recommendations


def status_from_diagnostics(diagnostics: list[dict[str, Any]]) -> str:
    severities = {diag.get("severity") for diag in diagnostics}
    if "critical" in severities:
        return "critical"
    if "warning" in severities:
        return "degraded"
    return "stable"
