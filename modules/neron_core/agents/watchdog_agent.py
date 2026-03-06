# agents/watchdog_agent.py
# Neron Core - Watchdog natif v2 avec détecteur d'anomalies

import asyncio
import json
import logging
import os
import sqlite3
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import psutil
from agents.base_agent import get_logger

logger = get_logger("watchdog_agent")

CHECK_INTERVAL  = int(os.getenv("WATCHDOG_INTERVAL",   "60"))
CPU_ALERT_PCT   = float(os.getenv("WATCHDOG_CPU_ALERT", "85"))
RAM_ALERT_PCT   = float(os.getenv("WATCHDOG_RAM_ALERT", "85"))
DISK_ALERT_PCT  = float(os.getenv("WATCHDOG_DISK_ALERT","90"))
ALERT_COOLDOWN  = 300   # secondes entre deux alertes identiques
DB_PATH              = os.getenv("MEMORY_DB_PATH", "/mnt/usb-storage/Neron_AI/data/memory.db")
WATCHDOG_BOT_TOKEN   = os.getenv("WATCHDOG_BOT_TOKEN", "")
WATCHDOG_CHAT_ID     = os.getenv("WATCHDOG_CHAT_ID", "")

_agents     = {}
_notify_fn  = None
_watchdog_bot_app = None
_task       = None
_last_alert: dict = {}
_alerted_anomalies: set = set()
_agent_failures: dict = {}   # {agent: [timestamp, ...]}
_pending_confirm: dict = {}  # {chat_id: {"action": ..., "expires": ...}}
AUTO_RESTART_THRESHOLD = 3
AUTO_RESTART_WINDOW    = 300  # secondes

# Alertes intelligentes
RAM_PROCESS_ALERT_MB   = 500   # alerte si process RAM > 500MB
OLLAMA_SILENT_MINUTES  = 10    # alerte si Ollama ne répond pas depuis X min
NERON_SILENT_HOURS     = 24    # alerte si aucune conversation depuis X heures
_last_ollama_ok: float = 0.0   # timestamp dernière réponse Ollama OK
_last_conversation: float = 0.0  # timestamp dernière conversation
_cpu_high_count: int = 0          # compteur checks CPU élevé consécutifs
_mute_until: float = 0.0          # timestamp fin de mute alertes
CPU_HIGH_CONSECUTIVE = 3          # alerter seulement après N checks consécutifs
AUTO_RESTART_WINDOW    = 300  # secondes
_start_time: float = time.monotonic()


# ─── DB EVENTS ────────────────────────────────────────────

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def log_event(type_: str, service: str = None, message: str = None, data: dict = None):
    """Enregistre un event watchdog dans la DB"""
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO events (type, service, message, data) VALUES (?, ?, ?, ?)",
                (type_, service, message, json.dumps(data or {}))
            )
            conn.commit()
    except Exception as e:
        logger.error(f"log_event error: {e}")

def read_events(days: int = 7) -> List[Dict]:
    """Lit les events des N derniers jours"""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE timestamp > datetime('now', ? || ' days') ORDER BY timestamp ASC",
                (f"-{days}",)
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["data"] = json.loads(d["data"]) if d["data"] else {}
                except Exception:
                    d["data"] = {}
                result.append(d)
            return result
    except Exception as e:
        logger.error(f"read_events error: {e}")
        return []


# ─── SETUP ────────────────────────────────────────────────

def setup(agents: dict, notify_fn):
    global _agents, _notify_fn
    _agents    = agents
    _notify_fn = notify_fn


# ─── NOTIFICATIONS ────────────────────────────────────────

async def _notify(msg: str, level: str = "warning", key: str = None):
    if key:
        last = _last_alert.get(key, 0)
        if time.monotonic() - last < ALERT_COOLDOWN:
            return
        _last_alert[key] = time.monotonic()
    logger.warning(f"[watchdog] {msg}")
    # Envoyer via le bot watchdog dédié
    if _watchdog_bot_app and WATCHDOG_CHAT_ID:
        try:
            icons = {"info": "ℹ️", "warning": "⚠️", "alert": "🔴"}
            icon = icons.get(level, "📢")
            await _watchdog_bot_app.bot.send_message(
                chat_id=WATCHDOG_CHAT_ID,
                text=f"{icon} {msg}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Erreur notification watchdog bot: {e}")
    elif _notify_fn:
        try:
            await _notify_fn(msg, level)
        except Exception as e:
            logger.error(f"Erreur notification fallback: {e}")


# ─── CHECKS SYSTÈME ───────────────────────────────────────

async def _check_system() -> dict:
    cpu  = psutil.cpu_percent(interval=1)
    ram  = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    proc = psutil.Process(os.getpid())
    proc_ram = round(proc.memory_info().rss / 1024 / 1024)

    stats = {"cpu": cpu, "ram": ram, "disk": disk, "proc_ram_mb": proc_ram}

    # Log stats en DB
    log_event("check", message="system_stats", data=stats)

    if cpu  > CPU_ALERT_PCT:
        await _notify(f"⚠️ CPU élevé : {cpu}%",    "warning", key="cpu")
        log_event("instability", service="system", message=f"CPU élevé {cpu}%")
    if ram  > RAM_ALERT_PCT:
        await _notify(f"⚠️ RAM élevée : {ram}%",   "warning", key="ram")
        log_event("instability", service="system", message=f"RAM élevée {ram}%")
    if disk > DISK_ALERT_PCT:
        await _notify(f"🔴 Disque plein : {disk}%", "alert",   key="disk")
        log_event("instability", service="system", message=f"Disque plein {disk}%")

    return stats


async def _check_agents() -> List[str]:
    issues = []
    checks = {
        "llm": ("LLM (Ollama)", "check_connection"),
        "stt": ("STT (faster-whisper)", "check_connection"),
        "tts": ("TTS (espeak)", "check_connection"),
    }
    for key, (label, method) in checks.items():
        if key not in _agents:
            continue
        try:
            ok = await getattr(_agents[key], method)()
            if not ok:
                issues.append(label)
                log_event("crash", service=label, message=f"{label} inaccessible")
        except Exception as e:
            issues.append(label)
            log_event("crash", service=label, message=str(e))

    if issues:
        msg = "🔴 Agents en erreur : " + ", ".join(issues)
        await _notify(msg, "alert", key="agents_" + "_".join(issues))



    # Auto-restart si échecs répétés
    for issue in issues:
        key = issue.split()[0].lower()  # "llm", "stt", "tts"
        now = time.monotonic()
        _agent_failures.setdefault(key, [])
        _agent_failures[key].append(now)
        # Nettoyer les vieux échecs
        _agent_failures[key] = [t for t in _agent_failures[key] if now - t < AUTO_RESTART_WINDOW]
        if len(_agent_failures[key]) >= AUTO_RESTART_THRESHOLD:
            agent = _agents.get(key)
            if agent:
                logger.warning(f"Auto-restart {key} ({AUTO_RESTART_THRESHOLD} échecs en {AUTO_RESTART_WINDOW}s)")
                try:
                    ok = await agent.reload() if asyncio.iscoroutinefunction(agent.reload) else agent.reload()
                    status = "✅ réussi" if ok else "⚠️ incertain"
                    log_event("recovery", service=key, message=f"auto-restart {status}")
                    await _notify(f"🔄 Auto-restart {key} — {status}", "info", key=f"auto_restart_{key}")
                except Exception as e:
                    logger.error(f"Auto-restart {key} échoué: {e}")
                _agent_failures[key] = []  # reset

    return issues


# ─── DÉTECTEUR D'ANOMALIES ────────────────────────────────

class AnomalyDetector:
    """Détecte les patterns anormaux dans l'historique des events"""

    def detect_recurring_crash(self, entries: list) -> List[Dict]:
        anomalies = []
        crashes = [e for e in entries if e.get("type") == "crash"]
        by_service = defaultdict(list)
        for c in crashes:
            try:
                ts = datetime.strptime(c["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
                by_service[c["service"]].append(ts.hour)
            except Exception:
                continue
        for service, hours in by_service.items():
            if len(hours) < 3:
                continue
            for hour, count in Counter(hours).items():
                if count >= 3:
                    anomalies.append({
                        "type": "recurring_crash", "service": service,
                        "message": f"{service} crashe régulièrement vers {hour:02d}h ({count}x)"
                    })
        return anomalies

    def detect_cascade(self, entries: list) -> List[Dict]:
        anomalies = []
        crashes = sorted([e for e in entries if e.get("type") == "crash"], key=lambda x: x["timestamp"])
        i = 0
        while i < len(crashes):
            window = [crashes[i]]
            try:
                t0 = datetime.strptime(crashes[i]["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                i += 1; continue
            j = i + 1
            while j < len(crashes):
                try:
                    tj = datetime.strptime(crashes[j]["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
                    if (tj - t0).total_seconds() <= 60:
                        window.append(crashes[j]); j += 1
                    else:
                        break
                except Exception:
                    j += 1
            if len(window) >= 3:
                services = list({e["service"] for e in window if e.get("service")})
                anomalies.append({
                    "type": "cascade", "services": services,
                    "message": f"Cascade: {len(services)} agents tombés en 60s ({', '.join(services)})"
                })
                i = j
            else:
                i += 1
        return anomalies

    def detect_crash_after_restart(self, entries: list) -> List[Dict]:
        anomalies = []
        recoveries = [e for e in entries if e.get("type") == "recovery"]
        crashes    = [e for e in entries if e.get("type") == "crash"]
        for rec in recoveries:
            service = rec.get("service")
            try:
                t_rec = datetime.strptime(rec["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            for crash in crashes:
                if crash.get("service") != service:
                    continue
                try:
                    t_crash = datetime.strptime(crash["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
                    delta = (t_crash - t_rec).total_seconds()
                    if 0 < delta < 300:
                        anomalies.append({
                            "type": "crash_after_restart", "service": service,
                            "message": f"{service} retombé {round(delta)}s après recovery (instabilité)"
                        })
                except Exception:
                    continue
        return anomalies

    def detect_increasing_frequency(self, entries: list) -> List[Dict]:
        anomalies = []
        crashes = [e for e in entries if e.get("type") == "crash"]
        by_service = defaultdict(list)
        for c in crashes:
            try:
                ts = datetime.strptime(c["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
                by_service[c.get("service", "unknown")].append(ts)
            except Exception:
                continue
        for service, timestamps in by_service.items():
            if len(timestamps) < 4:
                continue
            timestamps.sort()
            intervals = [(timestamps[i+1]-timestamps[i]).total_seconds() for i in range(len(timestamps)-1)]
            if len(intervals) < 3:
                continue
            mid = len(intervals) // 2
            avg_first  = sum(intervals[:mid]) / mid
            avg_second = sum(intervals[mid:]) / (len(intervals) - mid)
            if avg_second < avg_first * 0.5 and avg_first > 60:
                anomalies.append({
                    "type": "increasing_frequency", "service": service,
                    "message": f"{service} crashe de + en + vite ({avg_first/60:.1f}min → {avg_second/60:.1f}min)"
                })
        return anomalies

    def detect_memory_leak(self, entries: list) -> List[Dict]:
        """Détecte croissance RAM du process principal"""
        anomalies = []
        checks = [e for e in entries if e.get("type") == "check"]
        ram_values = []
        for c in checks:
            v = c.get("data", {}).get("proc_ram_mb", 0)
            if v > 0:
                ram_values.append(v)
        if len(ram_values) < 10:
            return anomalies
        mid = len(ram_values) // 2
        avg_first  = sum(ram_values[:mid]) / mid
        avg_second = sum(ram_values[mid:]) / (len(ram_values) - mid)
        if avg_second > avg_first * 1.2 and (avg_second - avg_first) > 50:
            anomalies.append({
                "type": "memory_leak_pattern", "service": "neron_core",
                "message": f"RAM process en hausse {avg_first:.0f}MB → {avg_second:.0f}MB (possible memory leak)"
            })
        return anomalies

    def compute_health_score(self, entries: list) -> Dict:
        crashes       = [e for e in entries if e.get("type") == "crash"]
        manual        = [e for e in entries if e.get("type") == "manual_required"]
        instabilities = [e for e in entries if e.get("type") == "instability"]
        recoveries    = [e for e in entries if e.get("type") == "recovery"]

        score = 100.0
        score -= len(crashes) * 2
        score -= len(manual)  * 15
        score -= len(instabilities) * 5
        score += len(recoveries)    * 1
        score  = max(0.0, min(100.0, score))

        if   score >= 90: level = "🟢 Excellent"
        elif score >= 75: level = "🟡 Bon"
        elif score >= 50: level = "🟠 Dégradé"
        else:             level = "🔴 Critique"

        return {
            "score": round(score, 1), "level": level,
            "crashes": len(crashes), "manual_interventions": len(manual)
        }

    async def run_analysis(self, notify_fn, days: int = 7) -> List[Dict]:
        entries = read_events(days=days)
        all_anomalies = []

        for detector in [
            self.detect_recurring_crash,
            self.detect_cascade,
            self.detect_crash_after_restart,
            self.detect_increasing_frequency,
            self.detect_memory_leak,
        ]:
            try:
                all_anomalies.extend(detector(entries))
            except Exception as e:
                logger.error(f"Détecteur {detector.__name__}: {e}")

        for anomaly in all_anomalies:
            key = f"{anomaly['type']}_{anomaly.get('service','')}_{anomaly.get('message','')[:30]}"
            if key not in _alerted_anomalies:
                _alerted_anomalies.add(key)
                logger.warning(f"Anomalie: {anomaly['message']}")
                if notify_fn:
                    await notify_fn(f"🔍 <b>Anomalie</b>\n{anomaly['message']}", "warning")

        return all_anomalies


# ─── BOUCLE PRINCIPALE ────────────────────────────────────

_detector = AnomalyDetector()

async def _send_weekly_report():
    """Rapport hebdomadaire — envoyé le lundi à 08h00"""
    if not _watchdog_bot_app or not WATCHDOG_CHAT_ID:
        return
    try:
        from datetime import datetime, timedelta

        # Stats 7 derniers jours
        entries = read_events(days=7)
        crashes    = [e for e in entries if e.get("type") == "crash"]
        recoveries = [e for e in entries if e.get("type") == "recovery"]
        manuals    = [e for e in entries if e.get("type") == "manual_required"]
        instab     = [e for e in entries if e.get("type") == "instability"]
        auto_rst   = [e for e in recoveries if "auto-restart" in e.get("message","")]

        # Score actuel
        score = get_health_score()

        # Uptime
        elapsed = time.monotonic() - _start_time
        days_up  = int(elapsed // 86400)
        hours_up = int((elapsed % 86400) // 3600)

        # Agents les plus touchés
        crash_by_agent = {}
        for e in crashes:
            svc = e.get("service","inconnu")
            crash_by_agent[svc] = crash_by_agent.get(svc, 0) + 1
        top_crashes = sorted(crash_by_agent.items(), key=lambda x: x[1], reverse=True)

        # Construire le rapport
        lines = [
            f"📊 <b>Rapport hebdomadaire Néron</b>",
            f"Semaine du {(datetime.now() - timedelta(days=7)).strftime('%d/%m')} au {datetime.now().strftime('%d/%m/%Y')}",
            "",
            f"{score['level']} <b>Score santé : {score['score']}/100</b>",
            "",
            f"⏱ Uptime : {days_up}j {hours_up}h",
            f"🔴 Crashs : {len(crashes)}",
            f"✅ Recoveries : {len(recoveries)}",
            f"🔄 Auto-restarts : {len(auto_rst)}",
            f"🔧 Interventions manuelles : {len(manuals)}",
            f"⚠️ Instabilités : {len(instab)}",
        ]

        if top_crashes:
            lines.append("")
            lines.append("📋 <b>Agents touchés :</b>")
            for agent, count in top_crashes[:3]:
                lines.append(f"  • {agent} : {count} crash(s)")

        # Tendance vs semaine précédente
        entries_14 = read_events(days=14)
        last_week_crashes = len([e for e in entries_14
                                  if e.get("type") == "crash"
                                  and e not in entries])
        if last_week_crashes > 0:
            diff = len(crashes) - last_week_crashes
            trend = f"📈 +{diff}" if diff > 0 else f"📉 {diff}" if diff < 0 else "➡️ stable"
            lines.append("")
            lines.append(f"📈 Tendance crashs : {trend} vs semaine précédente")

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("Bonne semaine ! 🚀")

        await _watchdog_bot_app.bot.send_message(
            chat_id=WATCHDOG_CHAT_ID,
            text="\n".join(lines),
            parse_mode="HTML"
        )
        log_event("check", message="rapport_hebdomadaire")
        logger.info("Rapport hebdomadaire envoyé")
    except Exception as e:
        logger.error(f"Rapport hebdomadaire erreur: {e}")


async def _send_daily_report():
    """Envoie un rapport quotidien à heure fixe"""
    if not _watchdog_bot_app or not WATCHDOG_CHAT_ID:
        return
    try:
        sys_  = get_status()
        score = get_health_score()
        entries = read_events(days=1)
        crashes = len([e for e in entries if e.get("type") == "crash"])
        elapsed = time.monotonic() - _start_time
        h = int(elapsed // 3600)
        m = int((elapsed % 3600) // 60)

        await _watchdog_bot_app.bot.send_message(
            chat_id=WATCHDOG_CHAT_ID,
            text=(
                f"📊 <b>Rapport quotidien Néron</b>\n\n"
                f"{score['level']} — Score: {score['score']}/100\n"
                f"Uptime: {h}h {m}m\n"
                f"Crashs 24h: {crashes}\n"
                f"CPU: {sys_.get('cpu_pct')}% | RAM: {sys_.get('ram_pct')}%\n"
                f"Process: {sys_.get('process_ram_mb')}MB"
            ),
            parse_mode="HTML"
        )
        log_event("check", message="rapport_quotidien")
    except Exception as e:
        logger.error(f"Rapport quotidien erreur: {e}")


async def _watchdog_loop():
    logger.info(f"Watchdog démarré — intervalle {CHECK_INTERVAL}s")
    await asyncio.sleep(10)
    cycle = 0

    while True:
        try:
            stats  = await _check_system()
            issues = await _check_agents()

            logger.info(
                f"[watchdog] CPU={stats['cpu']}% RAM={stats['ram']}% "
                f"Disk={stats['disk']}% ProcRAM={stats['proc_ram_mb']}MB issues={len(issues)}"
            )

            # Analyse anomalies toutes les 10 cycles (~10min)
            cycle += 1
            if cycle % 10 == 0:
                await _detector.run_analysis(_notify_fn)

            # Rapports automatiques
            now = datetime.now()
            if now.hour == 8 and now.minute == 0 and now.second < CHECK_INTERVAL:
                await _send_daily_report()
                # Rapport hebdomadaire le lundi
                if now.weekday() == 0:
                    await _send_weekly_report()

        except Exception as e:
            logger.error(f"Watchdog loop error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)


async def start_watchdog():
    global _task, _start_time
    _start_time = time.monotonic()
    _task = asyncio.create_task(_watchdog_loop())
    logger.info("Watchdog task créée")

async def stop_watchdog():
    global _task
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    logger.info("Watchdog arrêté")

def get_status() -> dict:
    try:
        proc = psutil.Process(os.getpid())
        return {
            "cpu_pct":        psutil.cpu_percent(interval=0.1),
            "ram_pct":        psutil.virtual_memory().percent,
            "ram_used_mb":    round(psutil.virtual_memory().used / 1024 / 1024),
            "disk_pct":       psutil.disk_usage("/").percent,
            "process_ram_mb": round(proc.memory_info().rss / 1024 / 1024),
            "uptime_s":       round(time.monotonic()),
        }
    except Exception as e:
        return {"error": str(e)}

def get_health_score() -> dict:
    entries = read_events(days=7)
    return _detector.compute_health_score(entries)

def get_anomalies(days: int = 7) -> list:
    entries = read_events(days=days)
    results = []
    for detector in [
        _detector.detect_recurring_crash,
        _detector.detect_cascade,
        _detector.detect_crash_after_restart,
        _detector.detect_increasing_frequency,
        _detector.detect_memory_leak,
    ]:
        try:
            results.extend(detector(entries))
        except Exception:
            pass
    return results


# ─── BOT WATCHDOG (@Neron_Watchdog_bot) ──────────────────

from telegram import Update as TGUpdate
from telegram.ext import Application as TGApplication, CommandHandler as TGCommandHandler, ContextTypes as TGContextTypes

WATCHDOG_ALLOWED = set(os.getenv("WATCHDOG_CHAT_ID", "").split(","))

def _wdog_authorized(update) -> bool:
    if not WATCHDOG_ALLOWED or WATCHDOG_ALLOWED == {''}:
        return True
    return str(update.message.chat_id) in WATCHDOG_ALLOWED

async def _wdog_cmd_status(update, context):
    if not _wdog_authorized(update): return
    try:
        import httpx as _httpx
        import sqlite3 as _sqlite3

        sys_   = get_status()
        score  = get_health_score()

        # Agents
        ok_llm = await _agents["llm"].check_connection() if "llm" in _agents else False
        ok_stt = await _agents["stt"].check_connection() if "stt" in _agents else False
        ok_tts = await _agents["tts"].check_connection() if "tts" in _agents else False

        # Core (self)
        ok_core = True  # si on répond, le core tourne

        # Ollama
        try:
            async with _httpx.AsyncClient(timeout=3) as c:
                r = await c.get("http://localhost:11434/api/tags")
                ok_ollama = r.status_code == 200
        except Exception:
            ok_ollama = False

        # Mémoire SQLite
        try:
            conn = _sqlite3.connect(DB_PATH)
            conn.execute("SELECT COUNT(*) FROM memory")
            conn.close()
            ok_memory = True
        except Exception:
            ok_memory = False

        lines = ["📊 <b>Néron v2 — Watchdog</b>\n"]
        lines.append(f"{'✅' if ok_core   else '🔴'} Core")
        lines.append(f"{'✅' if ok_ollama else '🔴'} Ollama")
        lines.append(f"{'✅' if ok_llm    else '🔴'} LLM")
        lines.append(f"{'✅' if ok_stt    else '🔴'} STT")
        lines.append(f"{'✅' if ok_tts    else '🔴'} TTS")
        lines.append(f"{'✅' if ok_memory else '🔴'} Mémoire")
        lines.append(f"\n🖥 CPU: {sys_.get('cpu_pct')}% | RAM: {sys_.get('ram_pct')}%")
        lines.append(f"💾 Disque: {sys_.get('disk_pct')}% | Process: {sys_.get('process_ram_mb')}MB")
        lines.append(f"\n{score['level']} — Score: {score['score']}/100")
        await update.message.reply_text("\n".join(lines), parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def _wdog_cmd_score(update, context):
    if not _wdog_authorized(update): return
    score = get_health_score()
    await update.message.reply_text(
        f"🏥 <b>Score santé</b>\n\n{score['level']} — {score['score']}/100\n"
        f"Crashs 7j: {score['crashes']}\nInterventions: {score['manual_interventions']}",
        parse_mode='HTML'
    )

async def _wdog_cmd_anomalies(update, context):
    if not _wdog_authorized(update): return
    anomalies = get_anomalies(days=7)
    if not anomalies:
        await update.message.reply_text("✅ Aucune anomalie")
        return
    lines = [f"🔍 <b>Anomalies ({len(anomalies)})</b>\n"]
    for a in anomalies[:10]:
        lines.append(f"• {a.get('message')}")
    await update.message.reply_text("\n".join(lines), parse_mode='HTML')

async def _wdog_cmd_start(update, context):
    if not _wdog_authorized(update): return
    await update.message.reply_text(
        "🔍 <b>Néron Watchdog v2</b>\n\n"
        "Commandes disponibles:\n"
        "\n📊 <b>Monitoring</b>\n"
        "/status — état complet (Core, Ollama, agents)\n"
        "/score — score de santé 7 jours\n"
        "/anomalies — anomalies détectées\n"
        "/stats — graphique CPU/RAM 24h\n"
        "/trend — tendance 7j vs 7j précédents\n"
        "/uptime — temps de fonctionnement\n"
        "\n📋 <b>Historique</b>\n"
        "/history [agent] — historique events 7j\n"
        "/logs [n] — dernières lignes de log\n"
        "\n📊 <b>Rapports</b>\n"
        "/rapport — rapport quotidien immédiat\n"
        "/hebdo — rapport hebdomadaire immédiat\n"
        "\n🔧 <b>Actions</b>\n"
        "/restart &lt;agent&gt; — recharger un agent\n"
        "/confirm — confirmer une action\n"
        "/cancel — annuler une action\n"
        "\n❓ <b>Aide</b>\n"
        "/help — cette aide",
        parse_mode="HTML"
    )




async def _wdog_cmd_uptime(update, context):
    if not _wdog_authorized(update): return
    elapsed = time.monotonic() - _start_time
    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    sys_ = get_status()
    await update.message.reply_text(
        f"⏱ <b>Uptime</b>\n\nDémarré il y a {h}h {m}m {s}s\n"
        f"Process RAM: {sys_.get('process_ram_mb')}MB\n"
        f"CPU: {sys_.get('cpu_pct')}% | RAM sys: {sys_.get('ram_pct')}%",
        parse_mode="HTML"
    )


async def _wdog_cmd_history(update, context):
    if not _wdog_authorized(update): return
    service = context.args[0].lower() if context.args else None
    entries = read_events(days=7)
    if service:
        entries = [e for e in entries if e.get("service","").lower() == service]
    if not entries:
        await update.message.reply_text(f"📭 Aucun event{' pour ' + service if service else ''}")
        return
    recent = entries[-10:]
    icons = {"crash":"🔴","recovery":"✅","instability":"⚠️","check":"📊","restart":"🔄"}
    lines = [f"📋 <b>Historique{' — '+service if service else ''}</b> ({len(entries)} events 7j)\n"]
    for e in recent:
        icon = icons.get(e.get("type",""),"•")
        ts   = e.get("timestamp","")[:16]
        svc  = e.get("service","") or ""
        msg  = e.get("message","")[:40]
        lines.append(f"{icon} {ts} {svc} {msg}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def _wdog_cmd_logs(update, context):
    if not _wdog_authorized(update): return
    import os as _os
    log_path = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../../../logs/neron_core.log"))
    try:
        n = min(int(context.args[0]) if context.args else 20, 50)
        with open(log_path) as f:
            lines = f.readlines()
        last = [l.strip() for l in lines[-n:] if any(x in l for x in ["ERROR","WARNING","INFO"])]
        text = "\n".join(last[-20:])
        if len(text) > 3500:
            text = "..." + text[-3500:]
        await update.message.reply_text(f"📄 <b>Logs ({n} lignes)</b>\n\n<pre>{text}</pre>", parse_mode="HTML")
    except FileNotFoundError:
        await update.message.reply_text("❌ Fichier log introuvable")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def _wdog_cmd_stats(update, context):
    if not _wdog_authorized(update): return
    try:
        import re as _re
        entries = read_events(days=1)
        checks  = [e for e in entries if e.get("type") == "check" and "[watchdog]" in e.get("message","")]
        if len(checks) < 2:
            await update.message.reply_text("📊 Pas encore assez de données")
            return
        cpu_vals, ram_vals, labels = [], [], []
        for e in checks[-12:]:
            msg   = e.get("message","")
            cpu_m = _re.search(r"CPU=([\d.]+)%", msg)
            ram_m = _re.search(r"RAM=([\d.]+)%", msg)
            ts    = e.get("timestamp","")[11:16]
            if cpu_m and ram_m:
                cpu_vals.append(float(cpu_m.group(1)))
                ram_vals.append(float(ram_m.group(1)))
                labels.append(ts)
        def bar(val, width=15):
            filled = int(val / 100 * width)
            return "█" * filled + "░" * (width - filled)
        lines = ["📊 <b>Stats CPU / RAM (24h)</b>\n<pre>"]
        for ts, cpu, ram in zip(labels, cpu_vals, ram_vals):
            lines.append(f"{ts} CPU {bar(cpu)} {cpu:.1f}%")
            lines.append(f"     RAM {bar(ram)} {ram:.1f}%")
            lines.append("")
        lines.append("</pre>")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def _wdog_cmd_trend(update, context):
    if not _wdog_authorized(update): return
    try:
        from datetime import datetime as _dt, timedelta as _td
        entries_14 = read_events(days=14)
        now       = _dt.now()
        week_ago  = now - _td(days=7)
        this_week = [e for e in entries_14 if _dt.fromisoformat(e["timestamp"]) >= week_ago]
        last_week = [e for e in entries_14 if _dt.fromisoformat(e["timestamp"]) <  week_ago]
        def ct(lst, t): return len([e for e in lst if e.get("type") == t])
        def ti(a, b):
            d = a - b
            return f"📈 +{d}" if d > 0 else f"📉 {d}" if d < 0 else "➡️ ="
        score = get_health_score()
        lines = [
            "📈 <b>Tendance 7j vs 7j précédents</b>\n",
            f"🔴 Crashs      : {ct(this_week,'crash')} {ti(ct(this_week,'crash'),ct(last_week,'crash'))}",
            f"✅ Recoveries  : {ct(this_week,'recovery')} {ti(ct(this_week,'recovery'),ct(last_week,'recovery'))}",
            f"🔧 Interventions: {ct(this_week,'manual_required')} {ti(ct(this_week,'manual_required'),ct(last_week,'manual_required'))}",
            f"\n{score['level']} Score: {score['score']}/100",
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def _wdog_cmd_rapport(update, context):
    if not _wdog_authorized(update): return
    await update.message.reply_text("📊 Génération du rapport...")
    await _send_daily_report()


async def _wdog_cmd_rapport_hebdo(update, context):
    if not _wdog_authorized(update): return
    await update.message.reply_text("📊 Génération du rapport hebdomadaire...")
    await _send_weekly_report()


async def _wdog_cmd_config(update, context):
    if not _wdog_authorized(update): return
    import sys as _sys
    mod = _sys.modules[__name__]
    config_map = {
        "cpu":      "CPU_ALERT_PCT",
        "ram":      "RAM_ALERT_PCT",
        "disk":     "DISK_ALERT_PCT",
        "procram":  "RAM_PROCESS_ALERT_MB",
        "ollama":   "OLLAMA_SILENT_MINUTES",
        "silence":  "NERON_SILENT_HOURS",
        "interval": "CHECK_INTERVAL",
        "cooldown": "ALERT_COOLDOWN",
    }
    if not context.args:
        lines = ["⚙️ <b>Configuration Watchdog</b>\n"]
        for k, v in config_map.items():
            lines.append(f"{k:10} : {getattr(mod, v)}")
        lines.append("\nUsage: /config &lt;clé&gt; &lt;valeur&gt;")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /config <clé> <valeur>")
        return
    key = context.args[0].lower()
    if key not in config_map:
        await update.message.reply_text(f"❌ Clé inconnue: {key}\nDisponibles: {', '.join(config_map)}")
        return
    try:
        value   = float(context.args[1])
        var     = config_map[key]
        old_val = getattr(mod, var)
        setattr(mod, var, type(old_val)(value))
        await update.message.reply_text(f"✅ <b>{var}</b>: {old_val} → {getattr(mod, var)}", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def _wdog_cmd_mute(update, context):
    if not _wdog_authorized(update): return
    global _mute_until
    if not context.args:
        if _mute_until > time.monotonic():
            rem = int((_mute_until - time.monotonic()) / 60)
            await update.message.reply_text(f"🔕 Alertes coupées encore {rem} min\n/mute 0 pour réactiver")
        else:
            await update.message.reply_text("🔔 Alertes actives\nUsage: /mute <minutes>")
        return
    try:
        minutes = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Valeur invalide")
        return
    if minutes == 0:
        _mute_until = 0.0
        await update.message.reply_text("🔔 Alertes réactivées")
    else:
        _mute_until = time.monotonic() + minutes * 60
        await update.message.reply_text(f"🔕 Alertes coupées pendant {minutes} min")


async def _wdog_cmd_clear(update, context):
    if not _wdog_authorized(update): return
    chat_id = str(update.message.chat_id)
    _pending_confirm[chat_id] = {"action": "clear_events", "expires": time.monotonic() + 30}
    await update.message.reply_text(
        "⚠️ <b>Effacer tous les events ?</b>\n\nIrréversible.\n/confirm | /cancel\n<i>(expire 30s)</i>",
        parse_mode="HTML"
    )


async def _wdog_cmd_cancel(update, context):
    if not _wdog_authorized(update): return
    chat_id = str(update.message.chat_id)
    if chat_id in _pending_confirm:
        del _pending_confirm[chat_id]
        await update.message.reply_text("✅ Action annulée.")
    else:
        await update.message.reply_text("ℹ️ Aucune action en attente.")


async def _wdog_cmd_confirm(update, context):
    if not _wdog_authorized(update): return
    chat_id = str(update.message.chat_id)
    pending = _pending_confirm.get(chat_id)
    if not pending:
        await update.message.reply_text("❌ Aucune action en attente.")
        return
    if time.monotonic() > pending["expires"]:
        del _pending_confirm[chat_id]
        await update.message.reply_text("⏰ Confirmation expirée. Recommencez.")
        return
    action = pending["action"]
    del _pending_confirm[chat_id]
    if action == "restart_core":
        await update.message.reply_text("🔄 Redémarrage de Néron Core...")
        log_event("restart", service="core", message="restart manuel via Telegram")
        await _notify("🔄 Redémarrage Core déclenché via Telegram", "warning")
        await asyncio.sleep(1)
        import os as _os, sys as _sys
        _os.execv(_sys.executable, [_sys.executable] + _sys.argv)
    elif action == "clear_events":
        try:
            import sqlite3 as _sq
            conn = _sq.connect(DB_PATH)
            conn.execute("DELETE FROM events")
            conn.commit()
            conn.close()
            await update.message.reply_text("✅ Historique events effacé")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")


async def _wdog_cmd_restart(update, context):
    if not _wdog_authorized(update): return
    if not context.args:
        await update.message.reply_text("Usage: /restart <agent>\nAgents: core, llm, stt, tts, memory")
        return
    agent_name = context.args[0].lower()
    if agent_name == "core":
        chat_id = str(update.message.chat_id)
        _pending_confirm[chat_id] = {"action": "restart_core", "expires": time.monotonic() + 30}
        await update.message.reply_text(
            "⚠️ <b>Redémarrage complet de Néron Core</b>\n\n"
            "Confirmer avec /confirm ou annuler avec /cancel\n<i>(expire dans 30s)</i>",
            parse_mode="HTML"
        )
        return
    agent = _agents.get(agent_name)
    if not agent:
        await update.message.reply_text(f"❌ Agent inconnu: {agent_name}\nDisponibles: core, llm, stt, tts, memory")
        return
    await update.message.reply_text(f"🔄 Rechargement de {agent_name}...")
    try:
        ok = await agent.reload() if asyncio.iscoroutinefunction(agent.reload) else agent.reload()
        if ok:
            log_event("recovery", service=agent_name, message="reload manuel via Telegram")
            await update.message.reply_text(f"✅ {agent_name} rechargé avec succès")
        else:
            await update.message.reply_text(f"⚠️ {agent_name} rechargé mais non confirmé")
    except Exception as e:
        log_event("crash", service=agent_name, message=f"reload échoué: {e}")
        await update.message.reply_text(f"❌ {e}")

async def start_watchdog_bot():
    global _watchdog_bot_app
    token = os.getenv("WATCHDOG_BOT_TOKEN")
    if not token:
        logger.warning("WATCHDOG_BOT_TOKEN non défini — bot watchdog désactivé")
        return

    _watchdog_bot_app = TGApplication.builder().token(token).build()

    _watchdog_bot_app.add_handler(TGCommandHandler("start",     _wdog_cmd_start))
    _watchdog_bot_app.add_handler(TGCommandHandler("help",      _wdog_cmd_start))
    _watchdog_bot_app.add_handler(TGCommandHandler("status",    _wdog_cmd_status))
    _watchdog_bot_app.add_handler(TGCommandHandler("score",     _wdog_cmd_score))
    _watchdog_bot_app.add_handler(TGCommandHandler("anomalies", _wdog_cmd_anomalies))
    _watchdog_bot_app.add_handler(TGCommandHandler("restart",   _wdog_cmd_restart))
    _watchdog_bot_app.add_handler(TGCommandHandler("confirm",   _wdog_cmd_confirm))
    _watchdog_bot_app.add_handler(TGCommandHandler("cancel",    _wdog_cmd_cancel))
    _watchdog_bot_app.add_handler(TGCommandHandler("config",    _wdog_cmd_config))
    _watchdog_bot_app.add_handler(TGCommandHandler("mute",      _wdog_cmd_mute))
    _watchdog_bot_app.add_handler(TGCommandHandler("clear",     _wdog_cmd_clear))
    _watchdog_bot_app.add_handler(TGCommandHandler("uptime",    _wdog_cmd_uptime))
    _watchdog_bot_app.add_handler(TGCommandHandler("logs",      _wdog_cmd_logs))
    _watchdog_bot_app.add_handler(TGCommandHandler("stats",     _wdog_cmd_stats))
    _watchdog_bot_app.add_handler(TGCommandHandler("trend",     _wdog_cmd_trend))
    _watchdog_bot_app.add_handler(TGCommandHandler("rapport",   _wdog_cmd_rapport))
    _watchdog_bot_app.add_handler(TGCommandHandler("hebdo",     _wdog_cmd_rapport_hebdo))
    _watchdog_bot_app.add_handler(TGCommandHandler("history",   _wdog_cmd_history))

    await _watchdog_bot_app.initialize()
    await _watchdog_bot_app.start()
    await _watchdog_bot_app.updater.start_polling()

    # Notification démarrage
    if WATCHDOG_CHAT_ID:
        try:
            await _watchdog_bot_app.bot.send_message(
                chat_id=WATCHDOG_CHAT_ID,
                text="🟢 <b>Néron v2 démarré</b>\nTous les agents sont en ligne.",
                parse_mode="HTML"
            )
        except Exception:
            pass

    logger.info("Bot Watchdog démarré (@Neron_Watchdog_bot)")


async def stop_watchdog_bot():
    global _watchdog_bot_app
    if _watchdog_bot_app:
        try:
            await _watchdog_bot_app.bot.send_message(
                chat_id=WATCHDOG_CHAT_ID,
                text="🔴 <b>Néron v2 arrêté</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await _watchdog_bot_app.updater.stop()
        await _watchdog_bot_app.stop()
        await _watchdog_bot_app.shutdown()
        logger.info("Bot Watchdog arrêté")
