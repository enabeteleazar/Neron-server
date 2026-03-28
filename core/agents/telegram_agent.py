# core/agents/telegram_agent.py
# Neron Core - Bot Telegram intégré (sans port séparé)

from __future__ import annotations

import asyncio
import json
import os
import time
import unicodedata
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

from core.constants import CODE_KEYWORDS
from core.agents.base_agent import get_logger
from core.world_model.publisher import publish
from core.agents.watchdog_agent import get_anomalies, get_health_score, get_status
from core.config import settings
from core.tools.twilio_tool import call as twilio_call

logger = get_logger("telegram_agent")

# ── Constantes ────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID
NERON_CORE_URL   = f"http://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
NERON_API_KEY    = settings.API_KEY
ALLOWED_CHAT_IDS = set(settings.TELEGRAM_CHAT_ID.split(","))

_WORKSPACE = Path(os.getenv("NERON_WORKSPACE", "/mnt/usb-storage/neron/workspace"))

# ── État global ───────────────────────────────────────────────────────────────
_agents: dict = {}
_telegram_app: Application | None = None

# ── Gestion des agents ─────────────────────────────────────────────────────────
def set_agents(agents: dict) -> None:
    """Injecte les agents depuis le code principal"""
    global _agents
    _agents = agents

# ── Auth ──────────────────────────────────────────────────────────────────────
def is_authorized(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS or ALLOWED_CHAT_IDS == {""}:
        return True
    return str(update.message.chat_id) in ALLOWED_CHAT_IDS

async def unauthorized(update: Update) -> None:
    await update.message.reply_text("⛔ Accès non autorisé")
    logger.warning("Accès refusé: chat_id=%s", update.message.chat_id)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _normalize(text: str) -> str:
    n = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in n if unicodedata.category(c) != "Mn")

async def _post_text(client: httpx.AsyncClient, text: str) -> dict:
    """Envoie une requête /input/text à Néron."""
    resp = await client.post(
        f"{NERON_CORE_URL}/input/text",
        json={"text": text},
        headers={"X-API-Key": NERON_API_KEY},
    )
    return resp.json()

# ── Commandes Telegram ─────────────────────────────────────────────────────────
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    await update.message.reply_text(
        "🤖 <b>Néron — Commandes disponibles</b>\n\n"
        "💬 Conversation: envoyez un message pour parler à Néron\n\n"
        "🔧 Code:\n"
        "/fix <fichier.py> — améliore un fichier\n"
        "/review — auto-review de tout le code\n"
        "/run <fichier.py> — exécute un script du workspace\n"
        "/workspace — liste les fichiers du workspace\n\n"
        "🧠 Mémoire:\n"
        "/memory — 5 derniers échanges\n\n"
        "🏠 Home Assistant:\n"
        "/ha_reload — recharge les entités HA\n\n"
        "📊 Système:\n"
        "/status — CPU, RAM, disque, tâches planifiées\n\n"
        "📞 Téléphonie:\n"
        "/call [message] — appel vocal via Twilio\n\n"
        "❓ /help — cette aide",
        parse_mode="HTML",
    )

async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    try:
        mem_agent = _agents.get("memory")
        if not mem_agent:
            await update.message.reply_text("❌ Agent mémoire non disponible")
            return
        entries = mem_agent.retrieve(limit=5)
        if not entries:
            await update.message.reply_text("📭 Mémoire vide")
            return
        lines = ["🧠 <b>Derniers échanges</b>\n"]
        for e in reversed(entries):
            lines.append(f"👤 {e['input'][:60]}")
            lines.append(f"🤖 {e['response'][:80]}\n")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {e}")

# ── Handler messages texte ────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    try:
        import core.agents.watchdog_agent as _wdog_mod
        _wdog_mod._last_conversation = time.monotonic()
    except Exception:
        pass

    user_message = update.message.text
    await update.message.chat.send_action("typing")
    sent = await update.message.reply_text("⏳ Néron réfléchit...")

    q = _normalize(user_message)
    is_code = any(_normalize(kw) in q for kw in CODE_KEYWORDS)

    try:
        if is_code:
            async with httpx.AsyncClient(timeout=600.0) as client:
                data = await _post_text(client, user_message)
                accumulated = data.get("response", "❌ Pas de réponse")
                await sent.edit_text(accumulated[:4096], parse_mode=None)
        else:
            accumulated = ""
            last_edit   = ""
            last_update = time.time()
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{NERON_CORE_URL}/input/stream",
                    json={"text": user_message},
                    headers={"X-API-Key": NERON_API_KEY},
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            data = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
                        token = data.get("token", "")
                        done = data.get("done", False)
                        accumulated += token
                        now = time.time()
                        if (now - last_update > 2.0 or done) and accumulated != last_edit:
                            try:
                                await sent.edit_text(accumulated or "⏳")
                                last_edit = accumulated
                                last_update = now
                            except Exception:
                                pass
                        if done:
                            break
            if not accumulated:
                await sent.edit_text("❌ Pas de réponse")
    except Exception as e:
        await sent.edit_text(f"❌ Erreur: {e}")

# ── Notifications ─────────────────────────────────────────────────────────────
async def send_notification(message: str, level: str = "info") -> None:
    if not _telegram_app or not TELEGRAM_CHAT_ID:
        return
    icons = {"info": "ℹ️", "warning": "⚠️", "alert": "🔴"}
    icon = icons.get(level, "📢")
    try:
        await _telegram_app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"{icon} {message}",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Erreur notification Telegram : %s", e)

# ── Lifecycle ─────────────────────────────────────────────────────────────────
async def start_bot() -> None:
    global _telegram_app
    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN manquant — bot désactivé")
        return

    _telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    _telegram_app.add_handler(CommandHandler("help", cmd_help))
    _telegram_app.add_handler(CommandHandler("memory", cmd_memory))
    _telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await _telegram_app.initialize()
    await _telegram_app.start()
    await _telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot Telegram démarré")
    publish("telegram_agent", {"status": "online", "bot": "telegram"})

    # Maintient le bot actif jusqu'à un arrêt externe
    await asyncio.Event().wait()

async def stop_bot() -> None:
    global _telegram_app
    if not _telegram_app:
        return
    try:
        await _telegram_app.updater.stop()
        await _telegram_app.stop()
        await _telegram_app.shutdown()
        logger.info("Bot Telegram arrêté")
    except Exception as e:
        logger.error("Erreur stop_bot : %s", e)
    finally:

        _telegram_app = None
