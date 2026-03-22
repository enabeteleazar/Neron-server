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
from tools.twilio_tool import call as twilio_call

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

    # Détecter requête code → input/text, sinon → input/stream
    import unicodedata
    def _norm(t):
        n = unicodedata.normalize("NFD", t.lower())
        return "".join(c for c in n if unicodedata.category(c) != "Mn")
    q = _norm(user_message)
    is_code = any(w in q for w in [
        "genere", "cree", "ecris", "ameliore", "optimise",
        "corrige", "analyse", "refactorise", "script", "module",
        "self review", "rollback", "restaure"
    ])

    try:
        if is_code:
            async with httpx.AsyncClient(timeout=600.0) as client:
                resp = await client.post(
                    f"{NERON_CORE_URL}/input/text",
                    json={"text": user_message},
                    headers={"X-API-Key": NERON_API_KEY}
                )
                data = resp.json()
                accumulated = data.get("response", "❌ Pas de réponse")
                await sent.edit_text(accumulated[:4096], parse_mode=None)
        else:
            accumulated = ""
            last_edit = ""
            last_update = time.time()
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

async def cmd_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return await unauthorized(update)
    message = " ".join(context.args) if context.args else "Appel de Néron. Aucun message spécifié."
    await update.message.reply_text(f"📞 Appel en cours...")
    result = twilio_call(message)
    if result["ok"]:
        await update.message.reply_text(f"✅ Appel lancé — SID: {result['sid']}")
    else:
        await update.message.reply_text(f"❌ Erreur : {result['error']}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return await unauthorized(update)
    sys_   = get_status()
    score  = get_health_score()
    from modules.scheduler import get_jobs
    jobs   = get_jobs()
    next_jobs = "\n".join(f"  • {j['name']} → {j['next_run'][:16]}" for j in jobs)
    await update.message.reply_text(
        f"📊 <b>Néron — Status</b>\n\n"
        f"{score['level']} Score : {score['score']}/100\n"
        f"🖥 CPU : {sys_.get('cpu_pct')}% | RAM : {sys_.get('ram_pct')}%\n"
        f"💾 Disque : {sys_.get('disk_pct')}%\n"
        f"⚙️ Process : {sys_.get('process_ram_mb')}MB\n\n"
        f"⏰ <b>Prochaines tâches</b>\n{next_jobs}",
        parse_mode="HTML"
    )


async def cmd_workspace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return await unauthorized(update)
    import os
    workspace = "/mnt/usb-storage/neron/workspace"
    files = sorted([f for f in os.listdir(workspace) if f.endswith(".py")])
    if not files:
        await update.message.reply_text("📂 Workspace vide")
        return
    lines = ["📂 <b>Workspace</b>\n"]
    for f in files:
        size = os.path.getsize(f"{workspace}/{f}")
        lines.append(f"• {f} ({size} bytes)")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return await unauthorized(update)
    if not context.args:
        await update.message.reply_text("Usage: /run <fichier.py>\nEx: /run eclipse.py")
        return

    filename = context.args[0]
    workspace = "/mnt/usb-storage/neron/workspace"
    filepath = f"{workspace}/{filename}"

    import os
    if not os.path.exists(filepath):
        await update.message.reply_text(f"❌ Fichier introuvable : {filename}\nFichiers disponibles :")
        files = [f for f in os.listdir(workspace) if f.endswith(".py")]
        if files:
            await update.message.reply_text("\n".join(f"• {f}" for f in files))
        return

    await update.message.reply_text(f"⚙️ Exécution de {filename}...")

    import subprocess
    try:
        result = subprocess.run(
            ["python3", filepath],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout.strip() or result.stderr.strip() or "(aucune sortie)"
        if len(output) > 3500:
            output = output[:3500] + "\n... (tronqué)"
        status = "✅" if result.returncode == 0 else "❌"
        await update.message.reply_text(
            f"{status} <b>{filename}</b>\n\n<pre>{output}</pre>",
            parse_mode="HTML"
        )
    except subprocess.TimeoutExpired:
        await update.message.reply_text(f"⏱ Timeout — {filename} a pris plus de 30 secondes")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {str(e)}")


async def start_bot():
    global _telegram_app

    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN manquant — bot désactivé")
        return

    _telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    _telegram_app.add_handler(CommandHandler("memory",    cmd_memory))
    _telegram_app.add_handler(CommandHandler("ha_reload", cmd_ha_reload))
    _telegram_app.add_handler(CommandHandler("call",      cmd_call))
    _telegram_app.add_handler(CommandHandler("run",       cmd_run))
    _telegram_app.add_handler(CommandHandler("status",    cmd_status))
    _telegram_app.add_handler(CommandHandler("workspace", cmd_workspace))
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
