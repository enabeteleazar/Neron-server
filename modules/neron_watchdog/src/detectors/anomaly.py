"""
Détection d'anomalies et patterns - WatchDog
Analyse la mémoire JSONL pour détecter des comportements anormaux
"""

import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

SERVICES = [
    "Neron Core", "Neron STT", "Neron Memory", "Neron TTS",
    "Neron LLM", "Neron Ollama", "Neron SearXNG", "Neron Web Voice"
]


class AnomalyDetector:
    """Détecte les anomalies et patterns dans l'historique WatchDog"""

    def __init__(self, memory, notifier):
        self.memory = memory
        self.notifier = notifier
        self._alerted = set()  # éviter les alertes répétées

    # ─────────────────────────────────────────────
    # 1. CRASH RÉCURRENT À LA MÊME HEURE
    # ─────────────────────────────────────────────
    def detect_recurring_crash(self, entries: list) -> List[Dict]:
        """Détecte si un service crashe toujours à la même heure (+/- 1h)"""
        anomalies = []
        crashes = [e for e in entries if e.get("type") == "crash"]

        by_service = defaultdict(list)
        for c in crashes:
            try:
                ts = datetime.strptime(c["timestamp"], "%Y-%m-%d %H:%M:%S")
                by_service[c["service"]].append(ts.hour)
            except Exception:
                continue

        for service, hours in by_service.items():
            if len(hours) < 3:
                continue
            hour_counter = Counter(hours)
            for hour, count in hour_counter.items():
                if count >= 3:
                    anomalies.append({
                        "type": "recurring_crash",
                        "service": service,
                        "hour": hour,
                        "occurrences": count,
                        "message": f"{service} crashe régulièrement vers {hour:02d}h ({count}x)"
                    })

        return anomalies

    # ─────────────────────────────────────────────
    # 2. DÉGRADATION PROGRESSIVE DU TEMPS DE RÉPONSE
    # ─────────────────────────────────────────────
    def detect_response_degradation(self, entries: list) -> List[Dict]:
        """Détecte une augmentation progressive du temps de réponse"""
        anomalies = []
        checks = [e for e in entries if e.get("type") == "check"]

        # Comparer moyenne première moitié vs deuxième moitié
        if len(checks) < 10:
            return anomalies

        mid = len(checks) // 2
        # Utiliser downtime comme proxy de dégradation
        restarts = [e for e in entries if e.get("type") == "restart"]

        by_service = defaultdict(list)
        for r in restarts:
            by_service[r["service"]].append(r.get("duration_sec", 0))

        for service, durations in by_service.items():
            if len(durations) < 4:
                continue
            mid = len(durations) // 2
            avg_first = sum(durations[:mid]) / mid
            avg_second = sum(durations[mid:]) / (len(durations) - mid)
            if avg_second > avg_first * 1.5:
                anomalies.append({
                    "type": "response_degradation",
                    "service": service,
                    "avg_before": round(avg_first, 1),
                    "avg_after": round(avg_second, 1),
                    "message": f"{service} temps de restart en hausse ({avg_first:.1f}s → {avg_second:.1f}s)"
                })

        return anomalies

    # ─────────────────────────────────────────────
    # 3. CASCADE DE CRASHS
    # ─────────────────────────────────────────────
    def detect_cascade(self, entries: list) -> List[Dict]:
        """Détecte plusieurs services qui tombent en même temps (fenêtre 60s)"""
        anomalies = []
        crashes = [e for e in entries if e.get("type") == "crash"]

        if len(crashes) < 2:
            return anomalies

        # Grouper par fenêtre de 60s
        crashes_sorted = sorted(crashes, key=lambda x: x["timestamp"])
        i = 0
        while i < len(crashes_sorted):
            window = [crashes_sorted[i]]
            t0 = datetime.strptime(crashes_sorted[i]["timestamp"], "%Y-%m-%d %H:%M:%S")

            j = i + 1
            while j < len(crashes_sorted):
                tj = datetime.strptime(crashes_sorted[j]["timestamp"], "%Y-%m-%d %H:%M:%S")
                if (tj - t0).total_seconds() <= 60:
                    window.append(crashes_sorted[j])
                    j += 1
                else:
                    break

            if len(window) >= 3:
                services = list({e["service"] for e in window})
                anomalies.append({
                    "type": "cascade",
                    "services": services,
                    "count": len(services),
                    "timestamp": crashes_sorted[i]["timestamp"],
                    "message": f"Cascade détectée: {len(services)} services tombés en 60s ({', '.join(services)})"
                })
                i = j
            else:
                i += 1

        return anomalies

    # ─────────────────────────────────────────────
    # 4. CRASH APRÈS REDÉMARRAGE RÉCENT
    # ─────────────────────────────────────────────
    def detect_crash_after_restart(self, entries: list) -> List[Dict]:
        """Détecte un service qui retombe moins de 5min après un restart réussi"""
        anomalies = []
        recoveries = [e for e in entries if e.get("type") == "recovery"]
        crashes = [e for e in entries if e.get("type") == "crash"]

        for recovery in recoveries:
            service = recovery["service"]
            try:
                t_recovery = datetime.strptime(recovery["timestamp"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

            for crash in crashes:
                if crash["service"] != service:
                    continue
                try:
                    t_crash = datetime.strptime(crash["timestamp"], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue

                delta = (t_crash - t_recovery).total_seconds()
                if 0 < delta < 300:  # moins de 5 minutes
                    anomalies.append({
                        "type": "crash_after_restart",
                        "service": service,
                        "delay_sec": round(delta),
                        "message": f"{service} retombé {round(delta)}s après restart (instabilité profonde)"
                    })

        return anomalies

    # ─────────────────────────────────────────────
    # 5. FRÉQUENCE CROISSANTE
    # ─────────────────────────────────────────────
    def detect_increasing_frequency(self, entries: list) -> List[Dict]:
        """Détecte un service qui crashe de plus en plus souvent"""
        anomalies = []
        crashes = [e for e in entries if e.get("type") == "crash"]

        by_service = defaultdict(list)
        for c in crashes:
            try:
                ts = datetime.strptime(c["timestamp"], "%Y-%m-%d %H:%M:%S")
                by_service[c["service"]].append(ts)
            except Exception:
                continue

        for service, timestamps in by_service.items():
            if len(timestamps) < 4:
                continue
            timestamps.sort()
            # Calculer les intervalles entre crashs
            intervals = [
                (timestamps[i+1] - timestamps[i]).total_seconds()
                for i in range(len(timestamps)-1)
            ]
            if len(intervals) < 3:
                continue
            # Comparer première moitié vs deuxième moitié
            mid = len(intervals) // 2
            avg_first = sum(intervals[:mid]) / mid
            avg_second = sum(intervals[mid:]) / (len(intervals) - mid)
            # Si les intervalles raccourcissent de 50%+
            if avg_second < avg_first * 0.5 and avg_first > 60:
                anomalies.append({
                    "type": "increasing_frequency",
                    "service": service,
                    "interval_before": round(avg_first / 60, 1),
                    "interval_after": round(avg_second / 60, 1),
                    "message": f"{service} crashe de plus en plus vite ({avg_first/60:.1f}min → {avg_second/60:.1f}min entre crashs)"
                })

        return anomalies

    # ─────────────────────────────────────────────
    # 6. CORRÉLATION CPU/RAM AVANT CRASH
    # ─────────────────────────────────────────────
    def detect_resource_correlation(self, entries: list) -> List[Dict]:
        """Détecte si les crashs surviennent après des pics CPU/RAM"""
        anomalies = []
        crashes = [e for e in entries if e.get("type") == "crash"]
        checks = [e for e in entries if e.get("type") == "check"]

        if not crashes or not checks:
            return anomalies

        high_cpu_before_crash = 0
        high_ram_before_crash = 0

        for crash in crashes:
            try:
                t_crash = datetime.strptime(crash["timestamp"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

            # Chercher les checks dans les 5 minutes avant le crash
            before = [
                c for c in checks
                if 0 < (t_crash - datetime.strptime(c["timestamp"], "%Y-%m-%d %H:%M:%S")).total_seconds() < 300
            ]

            for c in before:
                if c.get("cpu_percent", 0) > 85:
                    high_cpu_before_crash += 1
                if c.get("ram_percent", 0) > 80:
                    high_ram_before_crash += 1

        if len(crashes) >= 3 and high_cpu_before_crash >= len(crashes) * 0.6:
            anomalies.append({
                "type": "cpu_crash_correlation",
                "ratio": round(high_cpu_before_crash / len(crashes) * 100),
                "message": f"CPU élevé précède les crashs dans {round(high_cpu_before_crash/len(crashes)*100)}% des cas"
            })

        if len(crashes) >= 3 and high_ram_before_crash >= len(crashes) * 0.6:
            anomalies.append({
                "type": "ram_crash_correlation",
                "ratio": round(high_ram_before_crash / len(crashes) * 100),
                "message": f"RAM élevée précède les crashs dans {round(high_ram_before_crash/len(crashes)*100)}% des cas"
            })

        return anomalies

    # ─────────────────────────────────────────────
    # 7. CRASH APRÈS LONGUE DURÉE (MEMORY LEAK)
    # ─────────────────────────────────────────────
    def detect_memory_leak_pattern(self, entries: list) -> List[Dict]:
        """Détecte si un service tombe toujours après X heures de fonctionnement"""
        anomalies = []

        by_service = defaultdict(list)
        recoveries = [e for e in entries if e.get("type") == "recovery"]
        crashes = [e for e in entries if e.get("type") == "crash"]

        for recovery in recoveries:
            service = recovery["service"]
            try:
                t_up = datetime.strptime(recovery["timestamp"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

            next_crash = None
            for crash in crashes:
                if crash["service"] != service:
                    continue
                try:
                    t_crash = datetime.strptime(crash["timestamp"], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if t_crash > t_up:
                    if next_crash is None or t_crash < next_crash:
                        next_crash = t_crash

            if next_crash:
                uptime_hours = (next_crash - t_up).total_seconds() / 3600
                by_service[service].append(uptime_hours)

        for service, uptimes in by_service.items():
            if len(uptimes) < 3:
                continue
            avg_uptime = sum(uptimes) / len(uptimes)
            variance = sum((u - avg_uptime) ** 2 for u in uptimes) / len(uptimes)
            # Faible variance = pattern régulier
            if variance < (avg_uptime * 0.3) ** 2 and avg_uptime < 24:
                anomalies.append({
                    "type": "memory_leak_pattern",
                    "service": service,
                    "avg_uptime_hours": round(avg_uptime, 1),
                    "message": f"{service} tombe régulièrement après ~{avg_uptime:.1f}h (possible memory leak)"
                })

        return anomalies

    # ─────────────────────────────────────────────
    # 8. DÉPENDANCE EN CASCADE
    # ─────────────────────────────────────────────
    def detect_dependency_cascade(self, entries: list) -> List[Dict]:
        """Détecte si Core tombe → autres services tombent dans la foulée"""
        anomalies = []
        crashes = [e for e in entries if e.get("type") == "crash"]

        core_crashes = [
            e for e in crashes if e.get("service") == "Neron Core"
        ]

        for core_crash in core_crashes:
            try:
                t_core = datetime.strptime(core_crash["timestamp"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

            # Services tombés dans les 2 minutes suivantes
            followers = [
                e for e in crashes
                if e.get("service") != "Neron Core"
                and 0 < (datetime.strptime(e["timestamp"], "%Y-%m-%d %H:%M:%S") - t_core).total_seconds() < 120
            ]

            if len(followers) >= 2:
                services = [e["service"] for e in followers]
                anomalies.append({
                    "type": "dependency_cascade",
                    "trigger": "Neron Core",
                    "affected": services,
                    "message": f"Cascade dépendance: Core → {', '.join(services)}"
                })

        return anomalies

    # ─────────────────────────────────────────────
    # 9. JOUR DE LA SEMAINE
    # ─────────────────────────────────────────────
    def detect_weekday_pattern(self, entries: list) -> List[Dict]:
        """Détecte si les crashs sont concentrés sur certains jours"""
        anomalies = []
        crashes = [e for e in entries if e.get("type") == "crash"]

        if len(crashes) < 7:
            return anomalies

        day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        by_service = defaultdict(list)

        for c in crashes:
            try:
                ts = datetime.strptime(c["timestamp"], "%Y-%m-%d %H:%M:%S")
                by_service[c["service"]].append(ts.weekday())
            except Exception:
                continue

        for service, days in by_service.items():
            if len(days) < 4:
                continue
            day_counter = Counter(days)
            for day, count in day_counter.items():
                ratio = count / len(days)
                if ratio >= 0.5 and count >= 3:
                    anomalies.append({
                        "type": "weekday_pattern",
                        "service": service,
                        "day": day_names[day],
                        "ratio": round(ratio * 100),
                        "message": f"{service} crashe surtout le {day_names[day]} ({round(ratio*100)}% des crashs)"
                    })

        return anomalies

    # ─────────────────────────────────────────────
    # 10. HEURE DE POINTE
    # ─────────────────────────────────────────────
    def detect_peak_hour_pattern(self, entries: list) -> List[Dict]:
        """Détecte si les crashs sont concentrés sur des heures de pointe"""
        anomalies = []
        crashes = [e for e in entries if e.get("type") == "crash"]

        if len(crashes) < 6:
            return anomalies

        peak_hours = set(range(18, 23))  # 18h-22h
        peak_crashes = 0

        for c in crashes:
            try:
                ts = datetime.strptime(c["timestamp"], "%Y-%m-%d %H:%M:%S")
                if ts.hour in peak_hours:
                    peak_crashes += 1
            except Exception:
                continue

        ratio = peak_crashes / len(crashes)
        if ratio >= 0.6 and peak_crashes >= 3:
            anomalies.append({
                "type": "peak_hour_pattern",
                "ratio": round(ratio * 100),
                "peak_crashes": peak_crashes,
                "message": f"{round(ratio*100)}% des crashs surviennent entre 18h-22h (surcharge utilisateur)"
            })

        return anomalies

    # ─────────────────────────────────────────────
    # 11. SCORE DE SANTÉ GLOBAL
    # ─────────────────────────────────────────────
    def compute_health_score(self, entries: list) -> Dict:
        """Calcule un score de santé global /100"""
        crashes = [e for e in entries if e.get("type") == "crash"]
        restarts = [e for e in entries if e.get("type") == "restart"]
        manual = [e for e in entries if e.get("type") == "manual_required"]
        instabilities = [e for e in entries if e.get("type") == "instability"]

        score = 100.0

        # Pénalités
        score -= len(crashes) * 2          # -2 par crash
        score -= len(manual) * 15          # -15 par intervention manuelle
        score -= len(instabilities) * 5    # -5 par alerte instabilité

        # Bonus restarts réussis
        successful = sum(1 for e in restarts if e.get("success"))
        score += successful * 1            # +1 par restart réussi automatiquement

        score = max(0.0, min(100.0, score))

        if score >= 90:
            level = "🟢 Excellent"
        elif score >= 75:
            level = "🟡 Bon"
        elif score >= 50:
            level = "🟠 Dégradé"
        else:
            level = "🔴 Critique"

        return {
            "score": round(score, 1),
            "level": level,
            "crashes": len(crashes),
            "manual_interventions": len(manual)
        }

    # ─────────────────────────────────────────────
    # 12. TENDANCE HEBDOMADAIRE
    # ─────────────────────────────────────────────
    def detect_weekly_trend(self) -> Dict:
        """Compare cette semaine vs semaine précédente"""
        entries_this_week = self.memory.read_all(days=7)
        entries_last_week = self.memory.read_all(days=14)
        entries_prev_week = [
            e for e in entries_last_week
            if e not in entries_this_week
        ]

        crashes_this = len([e for e in entries_this_week if e.get("type") == "crash"])
        crashes_prev = len([e for e in entries_prev_week if e.get("type") == "crash"])

        if crashes_prev == 0:
            trend = "stable"
            delta = 0
        elif crashes_this > crashes_prev * 1.2:
            trend = "dégradation"
            delta = round((crashes_this - crashes_prev) / max(crashes_prev, 1) * 100)
        elif crashes_this < crashes_prev * 0.8:
            trend = "amélioration"
            delta = round((crashes_prev - crashes_this) / max(crashes_prev, 1) * 100)
        else:
            trend = "stable"
            delta = 0

        return {
            "trend": trend,
            "crashes_this_week": crashes_this,
            "crashes_prev_week": crashes_prev,
            "delta_percent": delta
        }

    # ─────────────────────────────────────────────
    # ANALYSE COMPLÈTE
    # ─────────────────────────────────────────────
    async def run_analysis(self, days: int = 7) -> List[Dict]:
        """Lance toutes les détections et notifie les nouvelles anomalies"""
        entries = self.memory.read_all(days=days)
        all_anomalies = []

        detectors = [
            self.detect_recurring_crash,
            self.detect_response_degradation,
            self.detect_cascade,
            self.detect_crash_after_restart,
            self.detect_increasing_frequency,
            self.detect_resource_correlation,
            self.detect_memory_leak_pattern,
            self.detect_dependency_cascade,
            self.detect_weekday_pattern,
            self.detect_peak_hour_pattern,
        ]

        for detector in detectors:
            try:
                results = detector(entries)
                all_anomalies.extend(results)
            except Exception as e:
                logger.error(f"Erreur détecteur {detector.__name__}: {e}")

        # Notifier les nouvelles anomalies
        for anomaly in all_anomalies:
            key = f"{anomaly['type']}_{anomaly.get('service', '')}_{anomaly.get('message', '')[:30]}"
            if key not in self._alerted:
                self._alerted.add(key)
                logger.warning(f"🔍 Anomalie détectée: {anomaly['message']}")
                await self.notifier.send_warning(
                    f"🔍 <b>Anomalie détectée</b>\n\n"
                    f"{anomaly['message']}\n"
                    f"<b>Heure:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

        return all_anomalies
