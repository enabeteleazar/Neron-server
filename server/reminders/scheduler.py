from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx

from reminders import db

logger = logging.getLogger("reminders.scheduler")

DEFAULT_POLL_SECONDS = 30.0


def _due_reminders(now: datetime) -> list[dict]:
    due = []
    for row in db.list_reminders(status_filter="pending", limit=1000):
        try:
            trigger = datetime.fromisoformat(row["trigger_at"])
        except ValueError:
            logger.warning("trigger_at illisible pour %s : %r", row["id"], row["trigger_at"])
            continue
        if trigger.tzinfo is None:
            trigger = trigger.replace(tzinfo=timezone.utc)
        if trigger <= now:
            due.append(row)
    return due


async def _notify_one(client: httpx.AsyncClient, core_url: str, api_key: str, reminder: dict) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    channel = reminder.get("channel") or "telegram"
    try:
        response = await client.post(
            f"{core_url}/notify",
            json={
                "message": reminder["content"],
                "level": "info",
                "channel": channel,
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        response.raise_for_status()
        db.update_reminder(
            reminder["id"],
            {"status": "triggered", "notified_at": now_iso, "triggered_at": now_iso},
        )
        logger.info("Rappel notifié : %s (%s)", reminder["id"], reminder["content"][:50])
    except Exception as exc:
        db.update_reminder(reminder["id"], {"notification_error": str(exc)})
        logger.warning("Échec notification rappel %s : %s", reminder["id"], exc)


async def run_scheduler_loop(interval: float = DEFAULT_POLL_SECONDS) -> None:
    core_url = os.getenv("NERON_CORE_URL", "").rstrip("/")
    api_key = os.getenv("NERON_API_KEY", "")

    if not core_url:
        logger.warning("NERON_CORE_URL absente — le scheduler de rappels ne peut pas notifier, boucle inactive")
        return

    logger.info("Scheduler de rappels démarré (intervalle %.0fs, core=%s)", interval, core_url)

    async with httpx.AsyncClient() as client:
        while True:
            try:
                now = datetime.now(timezone.utc)
                due = _due_reminders(now)
                for reminder in due:
                    await _notify_one(client, core_url, api_key, reminder)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Erreur boucle scheduler : %s", exc)

            await asyncio.sleep(interval)
