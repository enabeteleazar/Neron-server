# agents/telegram_agent.py
# Neron Core - Bot Telegram intégré (sans port séparé)

from config import settings
import json
import logging
import time
import httpx
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from agents.base_agent import get_logger
from agents.watchdog_agent import get_status, get_health_score, get_anomalies

logger = get_logger("telegram_agent")

TELEGRAM_TOKEN    = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID  = settings.TELEGRAM_CHAT_ID
NERON_CORE_URL    = f"http://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
NERON_API_KEY     = settings.API_KEY
ALLOWED_CHAT_IDS  = set(settings.TELEGRAM_CHAT_ID.split(","))

_agents = {}

def set_agents(agents: dict):
    global _agents
    _agents = agents


def is_authorized(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS or ALLOWED_CHAT_IDS == {''}:
        return True
    return str(update.message.chat_id) in ALLOWED_CHAT_IDS

async def unauthorized(update: Update):
    await update.message.reply_text("⛔ Accès non autorisé")
    logger.warning(f"Accès refusé: chat_id={update.message.chat_id}")


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


async def cmd_ha_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return await unauthorized(update)

    ha = _agents.get("ha")
    if not ha:
        await update.message.reply_text("❌ Agent Home Assistant non disponible")
        return

    await update.message.reply_text("🔄 Rechargement des entités Home Assistant...")
    try:
        count = await ha.reload()
        await update.message.reply_text(f"✅ Home Assistant rechargé — {count} entités")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur lors du rechargement : {str(e)}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return await unauthorized(update)

    try:
        from agents.watchdog_agent import _last_conversation as _wdog_lc
        import agents.watchdog_agent as _wdog_mod
        _wdog_mod._last_conversation = time.monotonic()
    except Exception:
        pass

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


_telegram_app: Application = None

async def start_bot():
    global _telegram_app

    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN manquant — bot désactivé")
        return

    _telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    _telegram_app.add_handler(CommandHandler("memory",    cmd_memory))
    _telegram_app.add_handler(CommandHandler("ha_reload", cmd_ha_reload))
    _telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await _telegram_app.initialize()
    await _telegram_app.start()
    await _telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot Telegram démarré")

async def stop_bot():
    global _telegram_app
    if _telegram_app:
        await _telegram_app.updater.stop()
        await _telegram_app.stop()
        await _telegram_app.shutdown()
        logger.info("Bot Telegram arrêté")

async def send_notification(message: str, level: str = "info"):
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
