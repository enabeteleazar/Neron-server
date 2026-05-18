from __future__ import annotations

import subprocess

SERVICES = {
    "core":             "neron-core",
    "llm":              "neron-llm",
    "doctor":           "neron-doctor",
    "ollama":           "ollama",
    "client":           "neron-vocal",
    "cognitive-loop":   "neron-cognitive-loop",
    "cognitive-daemon": "neron-cognitive-daemon.service",
}

class ServiceManager:
    def status(self, service: str) -> str:
        systemd_name = SERVICES.get(service, service)
        result = subprocess.run(
            ["systemctl", "is-active", systemd_name],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or result.stderr.strip()

    def status_all(self) -> dict[str, str]:
        return {name: self.status(name) for name in SERVICES.keys()}
