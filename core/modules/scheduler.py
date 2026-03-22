# core/scheduler.py
# Néron — Planificateur de tâches autonomes
#
# Tâches configurables via neron.yaml :
#   scheduler:
#     enabled: true
#     self_review_hour: 3        # heure auto-review (défaut 3h du matin)
#     memory_cleanup_days: 30    # rétention mémoire
#     daily_report_hour: 8       # rapport quotidien Telegram

import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings

logger = logging.getLogger("scheduler")

_scheduler: AsyncIOScheduler = None
_agents: dict = {}
_notify_fn = None


def setup(agents: dict, notify_fn):
    """Initialise le scheduler avec les agents et la fonction de notification."""
    global _agents, _notify_fn
    _agents    = agents
    _notify_fn = notify_fn


async def _task_self_review():
    """Auto-review nocturne — Néron analyse son code et liste les corrections."""
    logger.info("Scheduler: démarrage auto-review nocturne")
    code_agent = _agents.get("code")
    if not code_agent:
        logger.warning("Scheduler: code_agent non disponible")
        return

    try:
        result = await code_agent.execute("passe en revue tout le code de Néron", action="self_review")
        metadata = result.metadata or {}
        reports  = metadata.get("reports", [])
        avg      = metadata.get("avg_score", "?")
        now      = datetime.now().strftime("%d/%m/%Y")

        lines = [f"🔍 <b>Auto-review nocturne — {now}</b>\n"]
        lines.append(f"📊 Score moyen : {avg}/100 ({len(reports)} fichiers)\n")

        # Lister les fichiers avec issues
        files_with_issues = [
            r for r in reports
            if r.get("issues") and not r.get("error")
        ]

        if files_with_issues:
            lines.append("⚠️ <b>Corrections à effectuer :</b>\n")
            for r in sorted(files_with_issues, key=lambda x: x.get("quality_score") or 100):
                score  = r.get("quality_score", "?")
                fname  = r.get("file", "?").split("/")[-1]
                issues = r.get("issues", [])
                lines.append(f"📄 <b>{fname}</b> ({score}/100)")
                for issue in issues[:3]:  # max 3 issues par fichier
                    lines.append(f"  • {issue}")
                lines.append("")
        else:
            lines.append("✅ Aucune correction nécessaire")

        msg = "\n".join(lines)
        # Telegram limite à 4096 chars
        if len(msg) > 4000:
            msg = msg[:4000] + "\n... (tronqué)"

        if _notify_fn:
            await _notify_fn(msg, "info")
        logger.info(f"Auto-review terminée — {len(files_with_issues)} fichiers avec issues")
    except Exception as e:
        logger.error(f"Erreur auto-review : {e}")


async def _task_memory_cleanup():
    """Nettoyage de la mémoire ancienne."""
    logger.info("Scheduler: nettoyage mémoire")
    memory_agent = _agents.get("memory")
    if not memory_agent:
        return
    try:
        retention = getattr(settings, "MEMORY_RETENTION", 30)
        deleted = memory_agent.cleanup(days=retention)
        logger.info(f"Mémoire nettoyée : {deleted} entrées supprimées")
    except Exception as e:
        logger.error(f"Erreur nettoyage mémoire : {e}")


async def _task_daily_report():
    """Rapport quotidien envoyé sur Telegram."""
    logger.info("Scheduler: rapport quotidien")
    if not _notify_fn:
        return
    try:
        from agents.watchdog_agent import get_status, get_health_score
        sys_   = get_status()
        score  = get_health_score()
        now    = datetime.now().strftime("%d/%m/%Y %H:%M")

        msg = (
            f"📊 <b>Rapport quotidien Néron</b>\n"
            f"🕐 {now}\n\n"
            f"{score['level']} Score santé : {score['score']}/100\n"
            f"🖥 CPU : {sys_.get('cpu_pct')}% | RAM : {sys_.get('ram_pct')}%\n"
            f"💾 Disque : {sys_.get('disk_pct')}%\n"
            f"⚙️ Process : {sys_.get('process_ram_mb')}MB"
        )
        await _notify_fn(msg, "info")
    except Exception as e:
        logger.error(f"Erreur rapport quotidien : {e}")


async def _task_workspace_cleanup():
    """Nettoie les vieux fichiers du workspace généré."""
    import os
    from pathlib import Path
    workspace = Path("/mnt/usb-storage/neron/workspace")
    if not workspace.exists():
        return
    cutoff = datetime.now().timestamp() - (7 * 86400)  # 7 jours
    cleaned = 0
    for f in workspace.glob("*.py"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            cleaned += 1
    if cleaned:
        logger.info(f"Workspace : {cleaned} fichiers anciens supprimés")


def start():
    """Démarre le scheduler avec toutes les tâches configurées."""
    global _scheduler

    cfg = getattr(settings, '_cfg', {}).get("scheduler", {})
    enabled = str(cfg.get("enabled", True)).lower() == "true"

    if not enabled:
        logger.info("Scheduler désactivé dans neron.yaml")
        return

    self_review_hour   = int(cfg.get("self_review_hour",   3))
    daily_report_hour  = int(cfg.get("daily_report_hour",  8))

    _scheduler = AsyncIOScheduler(timezone="Europe/Paris")

    # Auto-review nocturne (défaut : 3h du matin)
    _scheduler.add_job(
        _task_self_review,
        CronTrigger(hour=self_review_hour, minute=0),
        id="self_review",
        name="Auto-review nocturne",
        replace_existing=True,
    )

    # Rapport quotidien (défaut : 8h)
    _scheduler.add_job(
        _task_daily_report,
        CronTrigger(hour=daily_report_hour, minute=0),
        id="daily_report",
        name="Rapport quotidien",
        replace_existing=True,
    )

    # Nettoyage mémoire (tous les lundis à 4h)
    _scheduler.add_job(
        _task_memory_cleanup,
        CronTrigger(day_of_week="mon", hour=4, minute=0),
        id="memory_cleanup",
        name="Nettoyage mémoire",
        replace_existing=True,
    )

    # Nettoyage workspace (tous les dimanches à 4h)
    _scheduler.add_job(
        _task_workspace_cleanup,
        CronTrigger(day_of_week="sun", hour=4, minute=0),
        id="workspace_cleanup",
        name="Nettoyage workspace",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        f"Scheduler démarré — "
        f"auto-review {self_review_hour}h | "
        f"rapport {daily_report_hour}h"
    )


def stop():
    """Arrête le scheduler proprement."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler arrêté")


def get_jobs() -> list[dict]:
    """Retourne la liste des tâches planifiées."""
    if not _scheduler:
        return []
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id":       job.id,
            "name":     job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else "N/A",
        })
    return jobs
