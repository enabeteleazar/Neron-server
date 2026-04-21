# agents/system_agent.py
# Agent SYSTEM_STATUS — interroge le watchdog natif (plus de service HTTP séparé)

from __future__ import annotations

from agents.base_agent import get_logger

logger = get_logger("system_agent")


async def handle_system_status(query: str) -> str:
    """
    Retourne un résumé de l'état système.
    FIX: appels directs aux fonctions natives du watchdog_agent
    au lieu d'appels HTTP vers un service externe supprimé.
    """
    # Import ici pour éviter les imports circulaires
    from agents.watchdog_agent import get_status, get_health_score, get_anomalies

    q = query.lower()
    try:
        if any(word in q for word in ["cpu", "ram", "memoire", "ressource", "process"]):
            return _format_resources(get_status())
        if any(word in q for word in ["anomalie", "probleme", "erreur", "crash"]):
            return _format_anomalies(get_anomalies(days=7))
        return _format_health(get_status(), get_health_score())
    except Exception as e:
        logger.error("handle_system_status error : %s", e)
        return "Impossible de récupérer l'état du système."


def _format_resources(sys_: dict) -> str:
    return (
        f"CPU : {sys_.get('cpu_pct')}% | "
        f"RAM : {sys_.get('ram_pct')}% ({sys_.get('ram_used_mb')} MB) | "
        f"Disque : {sys_.get('disk_pct')}% | "
        f"Process Néron : {sys_.get('process_ram_mb')} MB"
    )


def _format_health(sys_: dict, score: dict) -> str:
    return (
        f"{score['level']} — Score santé : {score['score']}/100\n"
        f"CPU : {sys_.get('cpu_pct')}% | RAM : {sys_.get('ram_pct')}% | "
        f"Disque : {sys_.get('disk_pct')}%"
    )


def _format_anomalies(anomalies: list) -> str:
    if not anomalies:
        return "✅ Aucune anomalie détectée sur les 7 derniers jours."
    lines = [f"🔍 {len(anomalies)} anomalie(s) détectée(s) :"]
    for a in anomalies[:5]:
        lines.append(f"  • {a.get('message', '?')}")
    return "\n".join(lines)
