from __future__ import annotations

import json
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil


WORLD_STATE_PATH = Path("/etc/neron/data/world_model_state.json")


@dataclass
class WorldModel:
    network: dict[str, Any] = field(default_factory=dict)
    host: dict[str, Any] = field(default_factory=dict)
    external_services: dict[str, Any] = field(default_factory=dict)
    environment_status: str = "unknown"
    diagnostics: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    last_update: float | None = None

    def collect_host(self) -> None:
        self.host = {
            "hostname": socket.gethostname(),
            "boot_time": psutil.boot_time(),
            "users": [user.name for user in psutil.users()],
            "load_average": self._load_average(),
        }

    def collect_network(self) -> None:
        self.network = {
            "interfaces": self._network_interfaces(),
            "default_gateway_reachable": self._ping("1.1.1.1"),
            "dns_reachable": self._resolve_dns("google.com"),
        }

    def collect_external_services(self) -> None:
        self.external_services = {
            "home_assistant": self._tcp_check("100.90.194.109", 8123),
            "ollama": self._tcp_check("127.0.0.1", 11434),
            "neron_llm_api": self._tcp_check("127.0.0.1", 8765),
            "neron_core_api": self._tcp_check("127.0.0.1", 8010),
        }

    def compute_status(self) -> None:
        self.diagnostics = []
        self.recommendations = []

        if not self.network.get("default_gateway_reachable"):
            self.diagnostics.append("La connectivité Internet semble indisponible.")
            self.recommendations.append("Vérifier la passerelle réseau ou la connexion Internet.")

        if not self.network.get("dns_reachable"):
            self.diagnostics.append("La résolution DNS semble indisponible.")
            self.recommendations.append("Vérifier la configuration DNS.")

        for service, state in self.external_services.items():
            if not state.get("reachable"):
                self.diagnostics.append(f"Service externe indisponible : {service}.")
                self.recommendations.append(f"Vérifier la disponibilité de {service}.")

        if self.diagnostics:
            self.environment_status = "degraded"
        else:
            self.environment_status = "stable"

    def refresh(self) -> None:
        self.collect_host()
        self.collect_network()
        self.collect_external_services()
        self.compute_status()
        self.last_update = time.time()

    def _load_average(self) -> dict[str, float | None]:
        try:
            load1, load5, load15 = psutil.getloadavg()
            return {
                "1min": round(load1, 2),
                "5min": round(load5, 2),
                "15min": round(load15, 2),
            }
        except Exception:
            return {
                "1min": None,
                "5min": None,
                "15min": None,
            }

    def _network_interfaces(self) -> dict[str, Any]:
        interfaces = {}

        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()

            for name, addr_list in addrs.items():
                ipv4 = [
                    item.address
                    for item in addr_list
                    if getattr(item, "family", None) == socket.AF_INET
                ]

                interfaces[name] = {
                    "up": stats.get(name).isup if name in stats else None,
                    "speed": stats.get(name).speed if name in stats else None,
                    "ipv4": ipv4,
                }

        except Exception:
            pass

        return interfaces

    def _ping(self, host: str) -> bool:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", host],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _resolve_dns(self, hostname: str) -> bool:
        try:
            socket.gethostbyname(hostname)
            return True
        except Exception:
            return False

    def _tcp_check(self, host: str, port: int, timeout: float = 1.0) -> dict[str, Any]:
        started = time.perf_counter()

        try:
            with socket.create_connection((host, port), timeout=timeout):
                latency_ms = round((time.perf_counter() - started) * 1000, 2)

                return {
                    "host": host,
                    "port": port,
                    "reachable": True,
                    "latency_ms": latency_ms,
                }

        except Exception as exc:
            return {
                "host": host,
                "port": port,
                "reachable": False,
                "error": str(exc),
            }

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "network": self.network,
            "external_services": self.external_services,
            "environment_status": self.environment_status,
            "diagnostics": self.diagnostics,
            "recommendations": self.recommendations,
            "last_update": self.last_update,
        }

    def save_state(self) -> None:
        WORLD_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

        tmp = WORLD_STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(WORLD_STATE_PATH)

    def summary(self) -> str:
        data = load_world_model_state()

        services = data.get("external_services", {})
        network = data.get("network", {})
        diagnostics = data.get("diagnostics", [])
        recommendations = data.get("recommendations", [])

        service_lines = []

        for name, state in services.items():
            status = "actif" if state.get("reachable") else "indisponible"
            latency = state.get("latency_ms")
            if latency is not None:
                service_lines.append(f"- {name} : {status} ({latency} ms)")
            else:
                service_lines.append(f"- {name} : {status}")

        diagnostics_text = (
            "\\n".join(f"  • {item}" for item in diagnostics)
            if diagnostics
            else "aucun"
        )

        recommendations_text = (
            "\\n".join(f"  • {item}" for item in recommendations)
            if recommendations
            else "aucune"
        )

        internet = "accessible" if network.get("default_gateway_reachable") else "indisponible"
        dns = "fonctionnel" if network.get("dns_reachable") else "indisponible"

        return f"""État du monde de Néron :
- Environnement : {data.get("environment_status")}
- Internet : {internet}
- DNS : {dns}

Services externes :
{chr(10).join(service_lines)}

Diagnostics :
{diagnostics_text}

Recommandations :
{recommendations_text}"""


def load_world_model_state() -> dict[str, Any]:
    if WORLD_STATE_PATH.exists():
        try:
            return json.loads(WORLD_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    model = WorldModel()
    model.refresh()
    model.save_state()
    return model.to_dict()


_WORLD_MODEL: WorldModel | None = None


def get_world_model() -> WorldModel:
    global _WORLD_MODEL

    if _WORLD_MODEL is None:
        _WORLD_MODEL = WorldModel()

    return _WORLD_MODEL
