# core/agents/telegram_agent.py

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from serverVNext.serverVNext.core.agents.base_agent import get_logger
from serverVNext.serverVNext.core.config import settings
from serverVNext.serverVNext.core.utils import normalize_text

logger = get_logger("telegram_agent")

# ── Config ────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID
NERON_CORE_URL   = f"http://localhost:{settings.SERVER_PORT}"
NERON_API_KEY    = settings.API_KEY
ALLOWED_CHAT_IDS = set(settings.TELEGRAM_CHAT_ID.split(",")) if settings.TELEGRAM_CHAT_ID else set()

PIPELINE_MODE = True

_WORKSPACE = Path(os.getenv("NERON_WORKSPACE", "/mnt/usb-storage/neron/workspace"))

# ── Auth ──────────────────────────────────────────────────────────────────
def is_authorized(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS or ALLOWED_CHAT_IDS == {""}:
        return True
    return str(update.message.chat_id) in ALLOWED_CHAT_IDS

async def unauthorized(update: Update) -> None:
    await update.message.reply_text("⛔ Accès non autorisé")

# ── HTTP helper ───────────────────────────────────────────────────────────
async def _post(client: httpx.AsyncClient, payload: dict) -> dict:
    headers = {}
    if NERON_API_KEY:  # ← Seulement ajouter le header si la clé existe
        headers["X-API-Key"] = NERON_API_KEY
    
    resp = await client.post(
        f"{NERON_CORE_URL}/input/text",
        json=payload,
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()

# ── Commandes ─────────────────────────────────────────────────────────────

async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /plan <tâche>")
        return
    sent = await update.message.reply_text("⏳ Planification en cours...")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            data = await _post(client, {"text": query, "mode": "plan"})
        await sent.edit_text(data.get("response", "❌")[:4096])
    except Exception as e:
        await sent.edit_text(f"❌ Erreur: {e}")


async def cmd_autopilot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /autopilot <tâche>")
        return
    await update.message.reply_text("🤖 Mode autonome lancé...")
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            data = await _post(client, {"text": query, "mode": "autopilot"})
        await update.message.reply_text(data.get("response", "❌")[:4096])
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {e}")


# ── Handler principal ─────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    user_message = update.message.text
    sent = await update.message.reply_text("⏳ Néron réfléchit...")
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            data = await _post(client, {
                "text": user_message,
                "mode": "pipeline" if PIPELINE_MODE else "standard",
            })
        await sent.edit_text(data.get("response", "❌ Pas de réponse")[:4096])
    except Exception as e:
        await sent.edit_text(f"❌ Erreur: {e}")


# ── Lifecycle ─────────────────────────────────────────────────────────────

async def start_bot() -> None:
    """
    Démarre le bot Telegram avec initialize/start/polling manuels.
    run_polling() est incompatible avec une boucle asyncio déjà en cours
    (_run_async dans app.py). On gère le cycle manuellement mais en
    supprimant le webhook et les updates en attente avant de démarrer,
    ce qui évite le 409 Conflict.
    """
    if not TELEGRAM_TOKEN:
        logger.warning("TOKEN Telegram manquant — bot désactivé")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("plan", cmd_plan))
    app.add_handler(CommandHandler("autopilot", cmd_autopilot))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    await app.initialize()

    # Supprime tout webhook et updates en attente avant de démarrer le polling.
    # C'est ce qui causait le 409 : une session de polling précédente encore
    # active côté Telegram.
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook supprimé, démarrage du polling...")

    await app.start()
    try:
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Bot Telegram démarré")
    except Exception as e:
        if "Conflict" in str(e) or "409" in str(e):
            logger.warning("Conflit détecté avec une autre instance du bot. Tentative de récupération...")
            # Attendre un peu puis réessayer
            await asyncio.sleep(5)
            try:
                await app.updater.start_polling(drop_pending_updates=True)
                logger.info("Bot Telegram démarré après récupération du conflit")
            except Exception as e2:
                logger.error(f"Impossible de démarrer le bot Telegram après conflit: {e2}")
                return
        else:
            logger.error(f"Erreur lors du démarrage du polling Telegram: {e}")
            return

    # Maintenir la boucle active jusqu'à l'arrêt du process
    await asyncio.Event().wait()


async def stop_bot() -> None:
    pass  # Le process est tué par le supervisor — pas besoin de cleanup explicite
