# agents/telegram_agent.py
# Neron Core - Bot Telegram intégré (sans port séparé)

import os
import json
import logging
import time
import httpx
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from agents.base_agent import get_logger

logger = get_logger("telegram_agent")

TELEGRAM_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID", "")
NERON_CORE_URL    = os.getenv("NERON_CORE_URL", "http://localhost:8000")
NERON_API_KEY     = os.getenv("NERON_API_KEY", "")
ALLOWED_CHAT_IDS  = set(os.getenv("TELEGRAM_CHAT_ID", "").split(","))

# Référence globale aux agents internes (injectée depuis app.py)
_agents = {}

def set_agents(agents: dict):
    """Injecte les références aux agents internes"""
    global _agents
    _agents = agents


# ─── SÉCURITÉ ─────────────────────────────────────────────

def is_authorized(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS or ALLOWED_CHAT_IDS == {''}:
        return True
    return str(update.message.chat_id) in ALLOWED_CHAT_IDS

async def unauthorized(update: Update):
    await update.message.reply_text("⛔ Accès non autorisé")
    logger.warning(f"Accès refusé: chat_id={update.message.chat_id}")


# ─── COMMANDES ────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return await unauthorized(update)
    await update.message.reply_text(
        "🧠 <b>Néron AI v2.0</b>\n\n"
        "Commandes:\n"
        "/status — état des agents\n"
        "/memory — derniers échanges\n"
        "/help — aide\n\n"
        "Ou envoyez un message pour parler à Néron !",
        parse_mode='HTML'
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return await unauthorized(update)
    try:
        llm_ok  = await _agents["llm"].check_connection()
        stt_ok  = await _agents["stt"].check_connection()
        tts_ok  = await _agents["tts"].check_connection()
        mem_ok  = len(_agents["memory"].retrieve(1)) >= 0

        lines = ["📊 <b>État des agents</b>\n"]
        lines.append(f"{'✅' if llm_ok  else '🔴'} LLM (Ollama)")
        lines.append(f"{'✅' if stt_ok  else '🔴'} STT (faster-whisper)")
        lines.append(f"{'✅' if tts_ok  else '🔴'} TTS (espeak)")
        lines.append(f"{'✅' if mem_ok  else '🔴'} Memory (SQLite)")
        await update.message.reply_text("\n".join(lines), parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")

async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return await unauthorized(update)
    try:
        entries = _agents["memory"].retrieve(limit=5)
        if not entries:
            await update.message.reply_text("📭 Mémoire vide")
            return
        lines = ["🧠 <b>Derniers échanges</b>\n"]
        for e in reversed(entries):
            lines.append(f"👤 {e['input'][:60]}")
            lines.append(f"🤖 {e['response'][:80]}\n")
        await update.message.reply_text("\n".join(lines), parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


# ─── MESSAGES ─────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Messages texte → streaming via /input/stream de core"""
    if not is_authorized(update): return await unauthorized(update)

    user_message = update.message.text
    await update.message.chat.send_action("typing")
    sent = await update.message.reply_text("⏳ Néron réfléchit...")

    accumulated = ""
    last_edit = ""
    last_update = time.time()

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{NERON_CORE_URL}/input/stream",
                json={"text": user_message},
                headers={"X-API-Key": NERON_API_KEY}
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except Exception:
                        continue
                    token = data.get("token", "")
                    done  = data.get("done", False)
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
        await sent.edit_text(f"❌ Erreur: {str(e)}")


# ─── DÉMARRAGE ────────────────────────────────────────────

_telegram_app: Application = None

async def start_bot():
    """Démarre le bot Telegram (appelé depuis lifespan de app.py)"""
    global _telegram_app

    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN manquant — bot désactivé")
        return

    _telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    _telegram_app.add_handler(CommandHandler("start",   cmd_start))
    _telegram_app.add_handler(CommandHandler("help",    cmd_help))
    _telegram_app.add_handler(CommandHandler("status",  cmd_status))
    _telegram_app.add_handler(CommandHandler("memory",  cmd_memory))
    _telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await _telegram_app.initialize()
    await _telegram_app.start()
    await _telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot Telegram démarré")

async def stop_bot():
    """Arrête le bot proprement"""
    global _telegram_app
    if _telegram_app:
        await _telegram_app.updater.stop()
        await _telegram_app.stop()
        await _telegram_app.shutdown()
        logger.info("Bot Telegram arrêté")

async def send_notification(message: str, level: str = "info"):
    """Envoie une notification Telegram"""
    if not _telegram_app or not TELEGRAM_CHAT_ID:
        return
    icons = {"info": "ℹ️", "warning": "⚠️", "alert": "🔴"}
    icon = icons.get(level, "📢")
    try:
        await _telegram_app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"{icon} {message}",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Erreur notification Telegram: {e}")
