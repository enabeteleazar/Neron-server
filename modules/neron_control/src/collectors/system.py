import psutil
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Metriques systeme collectees"""
    timestamp: datetime
    cpu_percent: float
    cpu_load_1: float
    cpu_load_5: float
    cpu_load_15: float
    ram_total_gb: float
    ram_used_gb: float
    ram_percent: float
    disks: list  # Liste de DiskMetric


@dataclass
class DiskMetric:
    """Metrique disque pour un point de montage"""
    mountpoint: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


class SystemCollector:
    """Collecte les metriques systeme via psutil"""

    # Points de montage a surveiller
    MOUNT_POINTS = ["/", "/mnt/Data", "/mnt/usb-storage", "/mnt/Backup"]

    def __init__(self, thresholds: dict = None):
        self.thresholds = thresholds or {
            "cpu_warn": 75,
            "cpu_critical": 90,
            "ram_warn": 80,
            "ram_critical": 95,
            "disk_warn": 75,
            "disk_critical": 90,
        }
        logger.info("📊 SystemCollector initialisé")

    def collect(self) -> SystemMetrics:
        """Collecter toutes les metriques systeme"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        load_avg = psutil.getloadavg()

        # RAM
        ram = psutil.virtual_memory()
        ram_total_gb = ram.total / (1024 ** 3)
        ram_used_gb = ram.used / (1024 ** 3)

        # Disques
        disks = []
        for mountpoint in self.MOUNT_POINTS:
            try:
                usage = psutil.disk_usage(mountpoint)
                disks.append(DiskMetric(
                    mountpoint=mountpoint,
                    total_gb=usage.total / (1024 ** 3),
                    used_gb=usage.used / (1024 ** 3),
                    free_gb=usage.free / (1024 ** 3),
                    percent=usage.percent
                ))
            except FileNotFoundError:
                pass  # Point de montage non disponible

        metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            cpu_load_1=load_avg[0],
            cpu_load_5=load_avg[1],
            cpu_load_15=load_avg[2],
            ram_total_gb=ram_total_gb,
            ram_used_gb=ram_used_gb,
            ram_percent=ram.percent,
            disks=disks
        )

        logger.debug(f"CPU: {cpu_percent}% | RAM: {ram.percent}%")
        return metrics

    def check_thresholds(self, metrics: SystemMetrics) -> list:
        """Verifier les seuils et retourner les alertes"""
        alerts = []

        # CPU
        if metrics.cpu_percent >= self.thresholds["cpu_critical"]:
            alerts.append(("critical", f"CPU critique: {metrics.cpu_percent:.1f}%"))
        elif metrics.cpu_percent >= self.thresholds["cpu_warn"]:
            alerts.append(("warning", f"CPU eleve: {metrics.cpu_percent:.1f}%"))

        # RAM
        if metrics.ram_percent >= self.thresholds["ram_critical"]:
            alerts.append(("critical", f"RAM critique: {metrics.ram_percent:.1f}%"))
        elif metrics.ram_percent >= self.thresholds["ram_warn"]:
            alerts.append(("warning", f"RAM elevee: {metrics.ram_percent:.1f}%"))

        # Disques
        for disk in metrics.disks:
            if disk.percent >= self.thresholds["disk_critical"]:
                alerts.append(("critical", f"Disque {disk.mountpoint} critique: {disk.percent:.1f}%"))
            elif disk.percent >= self.thresholds["disk_warn"]:
                alerts.append(("warning", f"Disque {disk.mountpoint} eleve: {disk.percent:.1f}%"))

        return alerts

    def format_report(self, metrics: SystemMetrics) -> str:
        """Formater un rapport lisible pour Telegram"""
        lines = [
            f"🖥️ <b>Métriques Système</b>",
            f"<b>Heure:</b> {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"<b>CPU:</b> {metrics.cpu_percent:.1f}%",
            f"<b>Load:</b> {metrics.cpu_load_1:.2f} / {metrics.cpu_load_5:.2f} / {metrics.cpu_load_15:.2f}",
            f"",
            f"<b>RAM:</b> {metrics.ram_used_gb:.1f}GB / {metrics.ram_total_gb:.1f}GB ({metrics.ram_percent:.1f}%)",
            f"",
            f"<b>Disques:</b>",
        ]
        for disk in metrics.disks:
            icon = "🔴" if disk.percent >= self.thresholds["disk_critical"] else "⚠️" if disk.percent >= self.thresholds["disk_warn"] else "✅"
            lines.append(f"  {icon} {disk.mountpoint}: {disk.used_gb:.1f}GB / {disk.total_gb:.1f}GB ({disk.percent:.1f}%)")

        return "\n".join(lines)
