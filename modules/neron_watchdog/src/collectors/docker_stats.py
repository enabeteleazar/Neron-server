"""
Collecteur de stats Docker par conteneur - WatchDog
Utilise l'API Docker via socket Unix
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

WATCHED_CONTAINERS = [
    "neron_core",
    "neron_stt",
    "neron_memory",
    "neron_tts",
    "neron_llm",
    "neron_ollama",
    "neron_searxng",
    "neron_web_voice",
]


@dataclass
class ContainerStats:
    name: str
    cpu_percent: float = 0.0
    ram_mb: float = 0.0
    ram_percent: float = 0.0
    net_rx_mb: float = 0.0
    net_tx_mb: float = 0.0
    status: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)


class DockerStatsCollector:
    """Collecte les stats de chaque conteneur via Docker API"""

    def __init__(self, socket_path: str = "/var/run/docker.sock"):
        self.socket_path = socket_path
        self._prev_cpu = {}  # pour calcul CPU delta
        logger.info("📊 DockerStatsCollector initialisé")

    def _compute_cpu_percent(self, stats: dict, container_name: str) -> float:
        """Calcule le % CPU à partir des deltas"""
        try:
            cpu_delta = (
                stats["cpu_stats"]["cpu_usage"]["total_usage"]
                - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            )
            system_delta = (
                stats["cpu_stats"]["system_cpu_usage"]
                - stats["precpu_stats"]["system_cpu_usage"]
            )
            num_cpus = stats["cpu_stats"].get("online_cpus") or len(
                stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1])
            )
            if system_delta > 0:
                return round((cpu_delta / system_delta) * num_cpus * 100, 2)
        except Exception:
            pass
        return 0.0

    def _compute_ram(self, stats: dict) -> tuple:
        """Retourne (ram_mb, ram_percent)"""
        try:
            usage = stats["memory_stats"]["usage"]
            limit = stats["memory_stats"]["limit"]
            # Soustraire le cache
            cache = stats["memory_stats"].get("stats", {}).get("cache", 0)
            real_usage = usage - cache
            ram_mb = round(real_usage / 1024 / 1024, 1)
            ram_percent = round(real_usage / limit * 100, 2) if limit > 0 else 0.0
            return ram_mb, ram_percent
        except Exception:
            return 0.0, 0.0

    def _compute_network(self, stats: dict) -> tuple:
        """Retourne (rx_mb, tx_mb)"""
        try:
            networks = stats.get("networks", {})
            rx = sum(v.get("rx_bytes", 0) for v in networks.values())
            tx = sum(v.get("tx_bytes", 0) for v in networks.values())
            return round(rx / 1024 / 1024, 2), round(tx / 1024 / 1024, 2)
        except Exception:
            return 0.0, 0.0

    async def collect_one(self, session: aiohttp.ClientSession, container: str) -> ContainerStats:
        """Collecte les stats d'un conteneur"""
        result = ContainerStats(name=container)
        try:
            # Stats instantanées (stream=false)
            async with session.get(
                f"http://localhost/containers/{container}/stats",
                params={"stream": "false"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result.cpu_percent = self._compute_cpu_percent(data, container)
                    result.ram_mb, result.ram_percent = self._compute_ram(data)
                    result.net_rx_mb, result.net_tx_mb = self._compute_network(data)
                    result.status = "running"
                elif resp.status == 404:
                    result.status = "not_found"
                else:
                    result.status = "error"
        except Exception as e:
            logger.debug(f"Stats {container}: {e}")
            result.status = "error"
        return result

    async def collect_all(self) -> Dict[str, ContainerStats]:
        """Collecte les stats de tous les conteneurs surveillés"""
        results = {}
        try:
            connector = aiohttp.UnixConnector(path=self.socket_path)
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = [self.collect_one(session, c) for c in WATCHED_CONTAINERS]
                stats_list = await asyncio.gather(*tasks, return_exceptions=True)
                for container, stats in zip(WATCHED_CONTAINERS, stats_list):
                    if isinstance(stats, ContainerStats):
                        results[container] = stats
                    else:
                        results[container] = ContainerStats(name=container, status="error")
        except Exception as e:
            logger.error(f"Erreur collecte Docker stats: {e}")
        return results

    def format_summary(self, stats: Dict[str, ContainerStats]) -> str:
        """Formate un résumé lisible des stats"""
        lines = ["📊 Stats conteneurs:"]
        for name, s in stats.items():
            if s.status == "running":
                lines.append(
                    f"  {name}: CPU {s.cpu_percent}% | "
                    f"RAM {s.ram_mb}MB ({s.ram_percent}%) | "
                    f"Net ↓{s.net_rx_mb}MB ↑{s.net_tx_mb}MB"
                )
            else:
                lines.append(f"  {name}: {s.status}")
        return "\n".join(lines)

    def check_thresholds(self, stats: Dict[str, ContainerStats]) -> List[tuple]:
        """Vérifie les seuils par conteneur et retourne les alertes"""
        alerts = []
        for name, s in stats.items():
            if s.status != "running":
                continue
            if s.cpu_percent > 95:
                alerts.append(("critical", f"🔴 {name}: CPU critique {s.cpu_percent}%"))
            elif s.cpu_percent > 80:
                alerts.append(("warning", f"⚠️ {name}: CPU élevé {s.cpu_percent}%"))
            if s.ram_percent > 90:
                alerts.append(("critical", f"🔴 {name}: RAM critique {s.ram_mb}MB ({s.ram_percent}%)"))
            elif s.ram_percent > 75:
                alerts.append(("warning", f"⚠️ {name}: RAM élevée {s.ram_mb}MB ({s.ram_percent}%)"))
        return alerts
