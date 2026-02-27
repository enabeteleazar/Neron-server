"""
Neron Telegram - Module central de communication
- Bot Telegram bidirectionnel
- API HTTP pour recevoir les notifications des autres modules
"""

import os
import logging
import asyncio
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NERON_CORE_URL = os.getenv("NERON_CORE_URL", "http://neron_core:8000")
NERON_MEMORY_URL = os.getenv("NERON_MEMORY_URL", "http://neron_memory:8002")
NERON_WATCHDOG_URL = os.getenv("NERON_WATCHDOG_URL", "http://neron_watchdog:8003")
NERON_API_KEY = os.getenv("NERON_API_KEY", "")
ALLOWED_CHAT_IDS = set(os.getenv("TELEGRAM_CHAT_ID", "").split(","))

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN manquant")

# Application Telegram globale
telegram_app: Application = None


# ─────────────────────────────────────────────
# SÉCURITÉ
# ─────────────────────────────────────────────
def is_authorized(update: Update) -> bool:
    """Vérifie si le chat_id est autorisé"""
    chat_id = str(update.message.chat_id)
    if not ALLOWED_CHAT_IDS or ALLOWED_CHAT_IDS == {''}:
        return True
    return chat_id in ALLOWED_CHAT_IDS


async def unauthorized(update: Update):
    await update.message.reply_text("⛔ Accès non autorisé")
    logger.warning(f"Accès refusé: chat_id={update.message.chat_id}")


# ─────────────────────────────────────────────
# COMMANDES
# ─────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    await update.message.reply_text(
        "🧠 <b>Néron AI</b>\n\n"
        "Commandes disponibles:\n"
        "/status — état des services\n"
        "/stats — CPU/RAM par conteneur\n"
        "/rapport — rapport immédiat\n"
        "/score — score de santé\n"
        "/anomalies — anomalies détectées\n"
        "/restart &lt;service&gt; — redémarrer un service\n"
        "/pause — mettre le watchdog en pause\n"
        "/resume — reprendre le watchdog\n"
        "/help — aide\n\n"
        "Ou envoyez un message pour parler à Néron !",
        parse_mode='HTML'
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{NERON_WATCHDOG_URL}/status", timeout=10)
            data = resp.json()
            lines = ["📊 <b>État des services</b>\n"]
            for service, info in data.get("services", {}).items():
                icon = "✅" if info.get("healthy") else "🔴"
                lines.append(f"{icon} {service}")
            await update.message.reply_text("\n".join(lines), parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{NERON_WATCHDOG_URL}/docker-stats", timeout=10)
            data = resp.json()
            lines = ["📊 <b>Stats conteneurs</b>\n"]
            for name, s in data.get("stats", {}).items():
                lines.append(f"  <b>{name}</b>: CPU {s.get('cpu')}% | RAM {s.get('ram_mb')}MB")
            await update.message.reply_text("\n".join(lines), parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_rapport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{NERON_WATCHDOG_URL}/rapport", timeout=30)
            await update.message.reply_text("📊 Rapport envoyé !", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{NERON_WATCHDOG_URL}/score", timeout=10)
            data = resp.json()
            await update.message.reply_text(
                f"🏥 <b>Score de santé</b>\n\n"
                f"{data.get('level')} — {data.get('score')}/100\n"
                f"Crashs 7j: {data.get('crashes')}\n"
                f"Interventions manuelles: {data.get('manual_interventions')}",
                parse_mode='HTML'
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_anomalies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{NERON_WATCHDOG_URL}/anomalies", timeout=30)
            data = resp.json()
            anomalies = data.get("anomalies", [])
            if not anomalies:
                await update.message.reply_text("✅ Aucune anomalie détectée")
                return
            lines = [f"🔍 <b>Anomalies détectées ({len(anomalies)})</b>\n"]
            for a in anomalies[:10]:
                lines.append(f"• {a.get('message')}")
            await update.message.reply_text("\n".join(lines), parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    if not context.args:
        await update.message.reply_text("Usage: /logs <service>\nEx: /logs neron_tts")
        return
    service = context.args[0]
    lines = int(context.args[1]) if len(context.args) > 1 else 30
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{NERON_WATCHDOG_URL}/logs/{service}",
                params={"lines": lines},
                timeout=15
            )
            data = resp.json()
            logs = data.get("logs", [])
            # Limiter à 50 lignes pour Telegram
            text = "\n".join(logs[-30:])
            if len(text) > 4000:
                text = text[-4000:]
            await update.message.reply_text(
                f"📋 <b>Logs {service}</b> (dernières {lines} lignes)\n\n<code>{text}</code>",
                parse_mode='HTML'
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    if not context.args:
        await update.message.reply_text("Usage: /history <service>\nEx: /history neron_tts")
        return
    service = context.args[0]
    # Convertir nom conteneur → nom service
    service_map = {
        "neron_core": "Neron Core",
        "neron_stt": "Neron STT",
        "neron_memory": "Neron Memory",
        "neron_tts": "Neron TTS",
        "neron_llm": "Neron LLM",
        "neron_ollama": "Neron Ollama",
        "neron_searxng": "Neron SearXNG",
        "neron_web_voice": "Neron Web Voice",
    }
    service_name = service_map.get(service, service)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{NERON_WATCHDOG_URL}/history/{service_name}",
                timeout=15
            )
            data = resp.json()
            events = data.get("events", [])
            total = data.get("total", 0)
            if not events:
                await update.message.reply_text(f"✅ Aucun événement pour {service_name}")
                return
            lines = [f"📊 <b>Historique {service_name}</b> ({total} événements)\n"]
            for e in events[-10:]:
                icon = {"crash": "🔴", "restart": "🔄", "instability": "⚠️", "recovery": "✅"}.get(e.get("type"), "•")
                ts = e.get("timestamp", "")[:16]
                lines.append(f"{icon} {ts} — {e.get('type')}")
            await update.message.reply_text("\n".join(lines), parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    if not context.args:
        await update.message.reply_text("Usage: /restart <service>\nEx: /restart neron_tts")
        return
    service = context.args[0]
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{NERON_WATCHDOG_URL}/restart/{service}",
                timeout=30
            )
            if resp.status_code == 200:
                await update.message.reply_text(f"🔄 Restart de {service} lancé")
            else:
                await update.message.reply_text(f"❌ Erreur: {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{NERON_WATCHDOG_URL}/pause", timeout=10)
            await update.message.reply_text("⏸️ Watchdog en pause")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized(update)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{NERON_WATCHDOG_URL}/resume", timeout=10)
            await update.message.reply_text("▶️ Watchdog repris")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Messages texte → neron_core"""
    if not is_authorized(update):
        return await unauthorized(update)

    user_message = update.message.text
    await update.message.chat.send_action("typing")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{NERON_CORE_URL}/input/text",
                json={"text": user_message},
                headers={"X-API-Key": NERON_API_KEY},
                timeout=120
            )
            if resp.status_code == 200:
                data = resp.json()
                await update.message.reply_text(
                    data.get("response", "Pas de réponse")
                )
            else:
                await update.message.reply_text(f"❌ Erreur {resp.status_code}")
    except httpx.TimeoutException:
        await update.message.reply_text("⏱️ Timeout — Néron prend trop de temps")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


# ─────────────────────────────────────────────
# FASTAPI — réception notifications
# ─────────────────────────────────────────────
class Notification(BaseModel):
    level: str  # info, warning, alert
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app

    # Démarrer le bot Telegram
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", cmd_start))
    telegram_app.add_handler(CommandHandler("help", cmd_help))
    telegram_app.add_handler(CommandHandler("status", cmd_status))
    telegram_app.add_handler(CommandHandler("stats", cmd_stats))
    telegram_app.add_handler(CommandHandler("rapport", cmd_rapport))
    telegram_app.add_handler(CommandHandler("score", cmd_score))
    telegram_app.add_handler(CommandHandler("anomalies", cmd_anomalies))
    telegram_app.add_handler(CommandHandler("restart", cmd_restart))
    telegram_app.add_handler(CommandHandler("pause", cmd_pause))
    telegram_app.add_handler(CommandHandler("resume", cmd_resume))
    telegram_app.add_handler(CommandHandler("logs", cmd_logs))
    telegram_app.add_handler(CommandHandler("history", cmd_history))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("🤖 Bot Telegram démarré")

    yield

    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()
    logger.info("🤖 Bot Telegram arrêté")


app = FastAPI(title="Neron Telegram", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "neron_telegram"}


@app.post("/notify")
async def notify(notif: Notification):
    """Recevoir une notification et l'envoyer sur Telegram"""
    if not TELEGRAM_CHAT_ID:
        raise HTTPException(400, "TELEGRAM_CHAT_ID non configuré")
    try:
        bot = telegram_app.bot
        icons = {"info": "ℹ️", "warning": "⚠️", "alert": "🔴"}
        icon = icons.get(notif.level, "📢")
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"{icon} {notif.message}",
            parse_mode='HTML'
        )
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8010, reload=False)
