# core/agents/telegram_agent.py

from __future__ import annotations

import asyncio
import json
import os
import time
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

from core.utils import normalize_text

logger = get_logger("telegram_agent")

# ── Config ────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID
NERON_CORE_URL   = f"http://localhost:{settings.SERVER_PORT}"
NERON_API_KEY    = settings.API_KEY
ALLOWED_CHAT_IDS = set(settings.TELEGRAM_CHAT_ID.split(","))

PIPELINE_MODE = True  # 🔥 active pipeline par défaut

_WORKSPACE = Path(os.getenv("NERON_WORKSPACE", "/mnt/usb-storage/neron/workspace"))

_agents: dict = {}
_telegram_app: Application | None = None

# ── Agents ────────────────────────────────────────────────────────────────
def set_agents(agents: dict) -> None:
    global _agents
    _agents = agents

# ── Auth ─────────────────────────────────────────────────────────────────
def is_authorized(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS or ALLOWED_CHAT_IDS == {""}:
        return True
    return str(update.message.chat_id) in ALLOWED_CHAT_IDS

async def unauthorized(update: Update) -> None:
    await update.message.reply_text("⛔ Accès non autorisé")

# ── HTTP helper ──────────────────────────────────────────────────────────
async def _post(client, payload: dict):
    resp = await client.post(
        f"{NERON_CORE_URL}/input/text",
        json=payload,
        headers={"X-API-Key": NERON_API_KEY},
    )
    resp.raise_for_status()
    return resp.json()

# ── Commandes Pipeline ───────────────────────────────────────────────────

async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)

    query = " ".join(context.args)
    if not query:
        return await update.message.reply_text("Usage: /plan <tâche>")

    async with httpx.AsyncClient(timeout=120.0) as client:
        data = await _post(client, {
            "text": query,
            "mode": "plan"
        })

    await update.message.reply_text(data.get("response", "❌"))

async def cmd_autopilot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)

    query = " ".join(context.args)
    if not query:
        return await update.message.reply_text("Usage: /autopilot <tâche>")

    await update.message.reply_text("🤖 Mode autonome lancé...")

    async with httpx.AsyncClient(timeout=600.0) as client:
        data = await _post(client, {
            "text": query,
            "mode": "autopilot"
        })

    await update.message.reply_text(data.get("response", "❌"))

# ── Handler principal ────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_authorized(update):
        return await unauthorized(update)

    user_message = update.message.text
    sent = await update.message.reply_text("⏳ Néron réfléchit...")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:

            payload = {
                "text": user_message,
                "mode": "pipeline" if PIPELINE_MODE else "standard"
            }

            data = await _post(client, payload)

            response = data.get("response", "❌ Pas de réponse")

            await sent.edit_text(response[:4096])

    except Exception as e:
        await sent.edit_text(f"❌ Erreur: {e}")

# ── Lifecycle ────────────────────────────────────────────────────────────
async def start_bot() -> None:
    global _telegram_app

    if not TELEGRAM_TOKEN:
        logger.warning("TOKEN Telegram manquant")
        return

    _telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    _telegram_app.add_handler(CommandHandler("plan", cmd_plan))
    _telegram_app.add_handler(CommandHandler("autopilot", cmd_autopilot))

    _telegram_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    await _telegram_app.initialize()
    await _telegram_app.start()
    await _telegram_app.updater.start_polling()

    logger.info("Bot Telegram démarré")

    await asyncio.Event().wait()

async def stop_bot() -> None:
    global _telegram_app

    if not _telegram_app:
        return

    await _telegram_app.updater.stop()
    await _telegram_app.stop()
    await _telegram_app.shutdown()

    _telegram_app = None
