"""
Rapport quotidien - WatchDog
Envoyé chaque jour à 19h via Telegram
"""

import logging
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger(__name__)

SERVICES = [
    "Neron Core", "Neron STT", "Neron Memory", "Neron TTS",
    "Neron LLM", "Neron Ollama", "Neron SearXNG", "Neron Web Voice"
]


class DailyReport:

    def __init__(self, notifier, memory, docker_stats=None, anomaly_detector=None, check_interval: int = 60):
        self.notifier = notifier
        self.memory = memory
        self.docker_stats = docker_stats
        self.anomaly_detector = anomaly_detector
        self.check_interval = check_interval
        self._last_report_date = None

    def should_send(self) -> bool:
        now = datetime.now()
        today = now.date()
        if now.hour == 19 and self._last_report_date != today:
            return True
        return False

    def _compute_uptime(self, service: str, entries: list, period_hours: int = 24) -> float:
        total_seconds = period_hours * 3600
        downtime_seconds = 0.0

        recoveries = [
            e for e in entries
            if e.get("type") == "recovery" and e.get("service") == service
        ]
        for r in recoveries:
            downtime_seconds += r.get("downtime_sec", 0)

        crashes = [e for e in entries if e.get("type") == "crash" and e.get("service") == service]
        unresolved = len(crashes) - len(recoveries)
        if unresolved > 0:
            crash_times = sorted([
                datetime.strptime(e["timestamp"], "%Y-%m-%d %H:%M:%S")
                for e in crashes
            ])
            if crash_times:
                downtime_seconds += (datetime.now() - crash_times[-1]).total_seconds()

        uptime = max(0.0, (total_seconds - downtime_seconds) / total_seconds * 100)
        return round(min(uptime, 100.0), 2)

    def generate(self, docker_stats_snapshot=None) -> str:
        now = datetime.now()
        entries = self.memory.read_all(days=1)
        entries_7d = self.memory.read_all(days=7)
        entries_14d = self.memory.read_all(days=14)

        crashes = [e for e in entries if e.get("type") == "crash"]
        restarts = [e for e in entries if e.get("type") == "restart"]
        instabilities = [e for e in entries if e.get("type") == "instability"]
        manual = [e for e in entries if e.get("type") == "manual_required"]

        crash_by_service = Counter(e["service"] for e in crashes)

        uptime_lines = ""
        for service in SERVICES:
            uptime = self._compute_uptime(service, entries)
            crash_count = crash_by_service.get(service, 0)
            if uptime >= 99.9:
                icon = "✅"
            elif uptime >= 95.0:
                icon = "🟡"
            else:
                icon = "🔴"
            uptime_lines += f"  {icon} {service}: {uptime}% ({crash_count} crash)\n"

        instable_services = list({e["service"] for e in instabilities})
        instable_text = ", ".join(instable_services) if instable_services else "Aucun"
        manual_text = str(len(manual)) if manual else "Aucune"

        # Score de santé
        health = self.anomaly_detector.compute_health_score(entries_7d) if self.anomaly_detector else {"score": 0, "level": "N/A", "crashes": 0}
        score_section = (
            f"\n<b>Score de santé</b>\n"
            f"  {health.get('level', 'N/A')} — {health.get('score', 0)}/100\n"
            f"  Crashs 7j: {health.get('crashes', 0)}\n"
        )

        # Tendance hebdomadaire
        crashes_7d = len([e for e in entries_7d if e.get("type") == "crash"])
        crashes_14d_prev = len([e for e in entries_14d if e.get("type") == "crash"]) - crashes_7d
        if crashes_14d_prev == 0:
            trend_icon = "➡️"
            trend_text = "Stable"
        elif crashes_7d < crashes_14d_prev:
            trend_icon = "📈"
            trend_text = f"Amélioration ({crashes_14d_prev} → {crashes_7d} crashs)"
        else:
            trend_icon = "📉"
            trend_text = f"Dégradation ({crashes_14d_prev} → {crashes_7d} crashs)"

        trend_section = (
            f"\n<b>Tendance hebdomadaire</b>\n"
            f"  {trend_icon} {trend_text}\n"
        )

        # Stats Docker
        docker_section = ""
        if docker_stats_snapshot:
            docker_section = "\n<b>Stats conteneurs</b>\n"
            for name, s in docker_stats_snapshot.items():
                if s.status == "running":
                    docker_section += f"  {name}: CPU {s.cpu_percent}% | RAM {s.ram_mb}MB\n"

        return (
            f"📊 <b>Rapport Quotidien WatchDog</b>\n"
            f"<b>Date:</b> {now.strftime('%d/%m/%Y')} a 19h00\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Resume 24h</b>\n"
            f"  🔴 Crashs totaux: {len(crashes)}\n"
            f"  🔄 Restarts: {len(restarts)}\n"
            f"  ⚠️ Alertes instabilite: {len(instabilities)}\n"
            f"  🚨 Interventions manuelles: {manual_text}\n\n"
            f"<b>Disponibilite par service</b>\n"
            f"{uptime_lines}\n"
            f"<b>Services instables</b>\n"
            f"  {instable_text}\n"
            f"{score_section}"
            f"{trend_section}"
            f"{docker_section}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Prochain rapport demain a 19h</i>"
        )

    async def send(self):
        try:
            snapshot = None
            if self.docker_stats:
                snapshot = await self.docker_stats.collect_all()
            report = self.generate(docker_stats_snapshot=snapshot)
            await self.notifier.send_info(report)
            self._last_report_date = datetime.now().date()
            logger.info("📊 Rapport quotidien envoye")
        except Exception as e:
            logger.error(f"Erreur envoi rapport: {e}")
