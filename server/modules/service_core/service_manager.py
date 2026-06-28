from __future__ import annotations

import subprocess

from core.runtime.governor import get_runtime_governor

SERVICES = {
    "core":             "neron-core",
    "llm":              "neron-llm",
    "doctor":           "neron-doctor",
    "ollama":           "ollama",
    "web":              "neron-web",
    "watchdog":         "neron-watchdog",
    "cognitive-daemon": "neron-cognitive-daemon.service",
}

class ServiceManager:
    def status(self, service: str) -> str:
        systemd_name = SERVICES.get(service, service)
        cmd = ["systemctl", "is-active", systemd_name]

        governor = get_runtime_governor()
        if not governor.authorize_system_command(
            actor="service_manager",
            command=cmd,
            reason=f"service status check: {systemd_name}",
        ):
            return "blocked_by_runtime_governor"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or result.stderr.strip()

    def status_all(self) -> dict[str, str]:
        return {name: self.status(name) for name in SERVICES.keys()}
