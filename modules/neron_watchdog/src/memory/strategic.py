"""
Mémoire stratégique JSONL - WatchDog
Journal structuré des événements pour analyse long terme
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)

MEMORY_FILE = "/app/data/memory.jsonl"
RETENTION_DAYS = 30


class StrategicMemory:
    """Gère le journal JSONL des événements WatchDog"""

    def __init__(self, path: str = MEMORY_FILE, retention_days: int = RETENTION_DAYS):
        self.path = Path(path)
        self.retention_days = retention_days
        self.path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"📝 Mémoire stratégique initialisée: {self.path} (rétention {retention_days}j)")

    def _write(self, entry: dict):
        entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erreur écriture mémoire: {e}")

    def record_crash(self, service: str, exit_code: str = "N/A"):
        self._write({"type": "crash", "service": service, "exit_code": exit_code})

    def record_restart(self, service: str, attempt: int, success: bool, duration: float = 0.0):
        self._write({"type": "restart", "service": service, "attempt": attempt,
                     "success": success, "duration_sec": round(duration, 2)})

    def record_instability(self, service: str, crash_count: int, window_min: int):
        self._write({"type": "instability", "service": service,
                     "crash_count": crash_count, "window_min": window_min})

    def record_manual_required(self, service: str, attempts: int):
        self._write({"type": "manual_required", "service": service, "attempts_failed": attempts})

    def record_recovery(self, service: str, downtime_sec: float):
        self._write({"type": "recovery", "service": service, "downtime_sec": round(downtime_sec, 2)})

    def record_check(self, healthy: int, total: int, cpu: float = 0.0, ram: float = 0.0):
        self._write({"type": "check", "healthy": healthy, "total": total,
                     "cpu_percent": round(cpu, 1), "ram_percent": round(ram, 1)})

    def purge_old_entries(self):
        if not self.path.exists():
            return
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        kept = []
        purged = 0
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        ts = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
                        if ts >= cutoff:
                            kept.append(line)
                        else:
                            purged += 1
                    except Exception:
                        kept.append(line)
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("\n".join(kept) + ("\n" if kept else ""))
            if purged > 0:
                logger.info(f"🗑️ Mémoire purgée: {purged} entrées supprimées (>{self.retention_days}j)")
        except Exception as e:
            logger.error(f"Erreur purge mémoire: {e}")

    def read_all(self, days: int = None) -> list:
        if not self.path.exists():
            return []
        entries = []
        cutoff = datetime.now() - timedelta(days=days) if days else None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if cutoff:
                            ts = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
                            if ts < cutoff:
                                continue
                        entries.append(entry)
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Erreur lecture mémoire: {e}")
        return entries

    def stats(self, days: int = 7) -> dict:
        entries = self.read_all(days=days)
        crashes = [e for e in entries if e["type"] == "crash"]
        restarts = [e for e in entries if e["type"] == "restart"]
        instabilities = [e for e in entries if e["type"] == "instability"]
        manual = [e for e in entries if e["type"] == "manual_required"]
        crash_by_service = Counter(e["service"] for e in crashes)
        return {
            "period_days": days,
            "total_crashes": len(crashes),
            "total_restarts": len(restarts),
            "successful_restarts": sum(1 for e in restarts if e.get("success")),
            "instability_alerts": len(instabilities),
            "manual_interventions": len(manual),
            "most_problematic": crash_by_service.most_common(3)
        }
