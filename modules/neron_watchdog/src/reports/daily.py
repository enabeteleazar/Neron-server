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

    def __init__(self, notifier, memory, check_interval: int = 60):
        self.notifier = notifier
        self.memory = memory
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

    def generate(self) -> str:
        now = datetime.now()
        entries = self.memory.read_all(days=1)

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
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Prochain rapport demain a 19h</i>"
        )

    async def send(self):
        try:
            report = self.generate()
            await self.notifier.send_info(report)
            self._last_report_date = datetime.now().date()
            logger.info("📊 Rapport quotidien envoye")
        except Exception as e:
            logger.error(f"Erreur envoi rapport: {e}")
