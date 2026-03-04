"""
Agent SYSTEM_STATUS - interroge neron_watchdog
"""
import httpx
import os
import logging

logger = logging.getLogger(__name__)

WATCHDOG_URL = os.getenv("NERON_WATCHDOG_URL", "http://neron_watchdog:8003")


async def handle_system_status(query: str) -> str:
    q = query.lower()
    try:
        async with httpx.AsyncClient(timeout=10) as client:

            if any(w in q for w in ["cpu", "ram", "memoire", "ressource"]):
                resp = await client.get(f"{WATCHDOG_URL}/docker-stats")
                data = resp.json()
                stats = data.get("stats", {})
                total_cpu = sum(s.get("cpu", 0) for s in stats.values())
                total_ram = sum(s.get("ram_mb", 0) for s in stats.values())
                top = sorted(stats.items(), key=lambda x: x[1].get("cpu", 0), reverse=True)[:3]
                top_str = ", ".join(f"{n} ({s.get('cpu', 0):.1f}%)" for n, s in top)
                return f"CPU total {total_cpu:.1f}%, RAM {total_ram:.0f}MB. Plus actifs : {top_str}."

            resp = await client.get(f"{WATCHDOG_URL}/status")
            data = resp.json()
            services = data.get("services", {})
            total = len(services)
            healthy = sum(1 for s in services.values() if s.get("healthy"))
            down = [n for n, s in services.items() if not s.get("healthy")]
            score = (healthy / total * 100) if total else 0

            if down:
                return f"Score {score:.0f}%. Probleme sur : {', '.join(down)}."
            return f"Systeme nominal. {total} services actifs, score {score:.0f}%."

    except Exception as e:
        logger.error(f"Erreur system_agent: {e}")
        return "Impossible de contacter le watchdog."
