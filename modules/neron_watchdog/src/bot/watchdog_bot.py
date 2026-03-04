"""
Bot Telegram Watchdog - commandes complètes
"""

import os
import logging
import asyncio
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

WATCHDOG_BOT_TOKEN = os.getenv("WATCHDOG_BOT_TOKEN")
WATCHDOG_CHAT_ID = os.getenv("WATCHDOG_CHAT_ID")
WATCHDOG_URL = "http://localhost:8003"


def is_authorized(update: Update) -> bool:
    return str(update.effective_chat.id) == str(WATCHDOG_CHAT_ID)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "🛡️ <b>Neron Watchdog</b>\n\n"
        "Commandes disponibles:\n"
        "/status — état des services\n"
        "/stats — CPU/RAM par conteneur\n"
        "/rapport — rapport immédiat\n"
        "/score — score de santé\n"
        "/anomalies — anomalies détectées\n"
        "/restart &lt;service&gt; — redémarrer un service\n"
        "/logs &lt;service&gt; — derniers logs\n"
        "/history &lt;service&gt; — historique crashs\n"
        "/pause — mettre en pause\n"
        "/resume — reprendre\n"
        "/help — aide",
        parse_mode="HTML"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await cmd_start(update, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{WATCHDOG_URL}/status")
            data = resp.json()
        services = data.get("services", {})
        lines = ["🛡️ <b>Status des services</b>\n"]
        healthy_count = 0
        for name, svc in services.items():
            icon = "✅" if svc.get("healthy") else "🔴"
            rt = svc.get("response_time", 0)
            lines.append(f"{icon} <code>{name:<20}</code> {rt*1000:>5.0f}ms")
            if svc.get("healthy"):
                healthy_count += 1
        total = len(services)
        score = (healthy_count / total * 100) if total else 0
        lines.append(f"\n📊 Score: {score:.0f}% ({healthy_count}/{total})")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{WATCHDOG_URL}/docker-stats")
            data = resp.json()
        stats = data.get("stats", {})
        lines = ["📊 <b>Stats conteneurs</b>\n"]
        total_cpu = 0
        total_ram = 0
        for name, s in stats.items():
            cpu = s.get("cpu", 0)
            ram = s.get("ram_mb", 0)
            total_cpu += cpu
            total_ram += ram
            lines.append(f"• <code>{name:<20}</code> {cpu:>5.1f}% | {ram:>6.0f}MB")
        lines.append(f"\n🖥️ CPU total: {total_cpu:.1f}%")
        lines.append(f"💾 RAM totale: {total_ram:.0f}MB")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_rapport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{WATCHDOG_URL}/rapport")
            data = resp.json()
        await update.message.reply_text(
            f"📋 <b>Rapport</b>\n\n{data.get('message', 'Rapport envoyé')}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{WATCHDOG_URL}/status")
            data = resp.json()
        score = data.get("health_score", 0)
        total = data.get("total_services", 0)
        healthy = data.get("healthy_services", 0)
        icon = "🟢" if score >= 80 else "🟡" if score >= 50 else "🔴"
        await update.message.reply_text(
            f"{icon} <b>Score de santé: {score:.0f}%</b>\n\n"
            f"Services OK: {healthy}/{total}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_anomalies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{WATCHDOG_URL}/anomalies")
            data = resp.json()
        anomalies = data.get("anomalies", [])
        if not anomalies:
            await update.message.reply_text("✅ Aucune anomalie détectée")
            return
        lines = ["⚠️ <b>Anomalies détectées</b>\n"]
        for a in anomalies:
            lines.append(f"• {a.get('service','?')}: {a.get('message','?')}")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /restart <service>")
        return
    service = context.args[0]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{WATCHDOG_URL}/restart/{service}")
            data = resp.json()
        await update.message.reply_text(
            f"🔄 <b>Restart {service}</b>\n{data.get('message', 'OK')}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /logs <service>")
        return
    service = context.args[0]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{WATCHDOG_URL}/logs/{service}?lines=30")
            data = resp.json()
        logs = data.get("logs", [])
        text = "\n".join(logs[-20:]) if logs else "Aucun log"
        await update.message.reply_text(
            f"📜 <b>Logs {service}</b>\n\n<pre>{text[-3000:]}</pre>",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /history <service>")
        return
    service = context.args[0]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{WATCHDOG_URL}/history/{service}")
            data = resp.json()
        events = data.get("events", [])
        if not events:
            await update.message.reply_text(f"✅ Aucun crash pour {service}")
            return
        lines = [f"📅 <b>Historique {service}</b>\n"]
        for e in events[-10:]:
            lines.append(f"• {e.get('timestamp','?')} — {e.get('type','?')}")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{WATCHDOG_URL}/pause")
        await update.message.reply_text("⏸️ Watchdog mis en pause")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{WATCHDOG_URL}/resume")
        await update.message.reply_text("▶️ Watchdog repris")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def run_bot():
    if not WATCHDOG_BOT_TOKEN:
        logger.warning("WATCHDOG_BOT_TOKEN non défini - bot désactivé")
        return
    app = Application.builder().token(WATCHDOG_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("rapport", cmd_rapport))
    app.add_handler(CommandHandler("score", cmd_score))
    app.add_handler(CommandHandler("anomalies", cmd_anomalies))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    logger.info("🤖 Bot Watchdog démarré avec toutes les commandes")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)
