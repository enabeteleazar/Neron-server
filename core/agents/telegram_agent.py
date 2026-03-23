# agents/telegram_agent.py
# Neron Core - Bot Telegram intégré (sans port séparé)

from __future__ import annotations

import asyncio
import json
import os
import time
import unicodedata
from pathlib import Path

from constants import CODE_KEYWORDS

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agents.base_agent import get_logger
from agents.watchdog_agent import get_anomalies, get_health_score, get_status
from config import settings
from tools.twilio_tool import call as twilio_call

logger = get_logger("telegram_agent")

# ── Constantes ────────────────────────────────────────────────────────────────

TELEGRAM_TOKEN   = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID
NERON_CORE_URL   = f"http://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
NERON_API_KEY    = settings.API_KEY
ALLOWED_CHAT_IDS = set(settings.TELEGRAM_CHAT_ID.split(","))

# FIX: workspace externalisé — plus de chemin hardcodé x3
_WORKSPACE = Path(os.getenv("NERON_WORKSPACE", "/mnt/usb-storage/neron/workspace"))

# ── État global ───────────────────────────────────────────────────────────────

_agents: dict = {}
_telegram_app: Application | None = None


def set_agents(agents: dict) -> None:
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


# ── Handlers commandes ────────────────────────────────────────────────────────

async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    try:
        entries = _agents["memory"].retrieve(limit=5)
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


async def cmd_ha_reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    ha = _agents.get("ha")
    if not ha:
        await update.message.reply_text("❌ Agent Home Assistant non disponible")
        return
    await update.message.reply_text("🔄 Rechargement des entités Home Assistant...")
    try:
        count = await ha.reload()
        await update.message.reply_text(f"✅ Home Assistant rechargé — {count} entités")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {e}")


async def cmd_call(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    message = " ".join(context.args) if context.args else "Appel de Néron. Aucun message spécifié."
    await update.message.reply_text("📞 Appel en cours...")
    result = twilio_call(message)
    if result["ok"]:
        await update.message.reply_text(f"✅ Appel lancé — SID: {result['sid']}")
    else:
        await update.message.reply_text(f"❌ Erreur : {result['error']}")


async def cmd_fix(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    if not context.args:
        await update.message.reply_text(
            "Usage: /fix <fichier.py>\nEx: /fix agents/system_agent.py"
        )
        return
    filepath = context.args[0]
    await update.message.reply_text(f"🔧 Amélioration de {filepath} en cours...")
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            data = await _post_text(client, f"améliore le fichier {filepath}")
            response = data.get("response", "❌ Pas de réponse")
            await update.message.reply_text(response[:4096], parse_mode=None)
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {e}")


async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    await update.message.reply_text("🔍 Auto-review en cours... (peut prendre plusieurs minutes)")
    from modules.scheduler import _task_self_review
    await _task_self_review()


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    sys_  = get_status()
    score = get_health_score()
    from modules.scheduler import get_jobs
    jobs      = get_jobs()
    next_jobs = "\n".join(f"  • {j['name']} → {j['next_run'][:16]}" for j in jobs)
    await update.message.reply_text(
        f"📊 <b>Néron — Status</b>\n\n"
        f"{score['level']} Score : {score['score']}/100\n"
        f"🖥 CPU : {sys_.get('cpu_pct')}% | RAM : {sys_.get('ram_pct')}%\n"
        f"💾 Disque : {sys_.get('disk_pct')}%\n"
        f"⚙️ Process : {sys_.get('process_ram_mb')}MB\n\n"
        f"⏰ <b>Prochaines tâches</b>\n{next_jobs}",
        parse_mode="HTML",
    )


async def cmd_workspace(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    if not _WORKSPACE.exists():
        await update.message.reply_text("📂 Workspace introuvable")
        return
    files = sorted(p for p in _WORKSPACE.glob("*.py"))
    if not files:
        await update.message.reply_text("📂 Workspace vide")
        return
    lines = ["📂 <b>Workspace</b>\n"]
    for f in files:
        lines.append(f"• {f.name} ({f.stat().st_size} bytes)")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)
    if not context.args:
        await update.message.reply_text("Usage: /run <fichier.py>\nEx: /run eclipse.py")
        return

    filename = Path(context.args[0]).name  # FIX: jail — on ne garde que le nom de fichier
    filepath = _WORKSPACE / filename

    if not filepath.exists():
        await update.message.reply_text(f"❌ Fichier introuvable : {filename}")
        files = [p.name for p in _WORKSPACE.glob("*.py")]
        if files:
            await update.message.reply_text("\n".join(f"• {f}" for f in sorted(files)))
        return

    await update.message.reply_text(f"⚙️ Exécution de {filename}...")

    # FIX: subprocess bloquant → asyncio.create_subprocess_exec()
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", str(filepath),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            await update.message.reply_text(
                f"⏱ Timeout — {filename} a pris plus de 30 secondes"
            )
            return

        output = (stdout.decode().strip() or stderr.decode().strip() or "(aucune sortie)")
        if len(output) > 3500:
            output = output[:3500] + "\n... (tronqué)"
        status = "✅" if proc.returncode == 0 else "❌"
        await update.message.reply_text(
            f"{status} <b>{filename}</b>\n\n<pre>{output}</pre>",
            parse_mode="HTML",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {e}")


# ── Handler messages texte ────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    # Mise à jour watchdog
    try:
        import agents.watchdog_agent as _wdog_mod
        _wdog_mod._last_conversation = time.monotonic()
    except Exception:
        pass

    user_message = update.message.text
    await update.message.chat.send_action("typing")
    sent = await update.message.reply_text("⏳ Néron réfléchit...")

    # FIX: CODE_KEYWORDS importé depuis constants.py — source de vérité unique
    q = _normalize(user_message)
    is_code = any(_normalize(kw) in q for kw in CODE_KEYWORDS)

    try:
        if is_code:
            async with httpx.AsyncClient(timeout=600.0) as client:
                data        = await _post_text(client, user_message)
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
                            data  = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
                        token        = data.get("token", "")
                        done         = data.get("done", False)
                        accumulated += token
                        now          = time.time()
                        if (now - last_update > 2.0 or done) and accumulated != last_edit:
                            try:
                                await sent.edit_text(accumulated or "⏳")
                                last_edit   = accumulated
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
    icon  = icons.get(level, "📢")
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
    _telegram_app.add_handler(CommandHandler("memory",    cmd_memory))
    _telegram_app.add_handler(CommandHandler("ha_reload", cmd_ha_reload))
    _telegram_app.add_handler(CommandHandler("call",      cmd_call))
    _telegram_app.add_handler(CommandHandler("run",       cmd_run))
    _telegram_app.add_handler(CommandHandler("status",    cmd_status))
    _telegram_app.add_handler(CommandHandler("review",    cmd_review))
    _telegram_app.add_handler(CommandHandler("fix",       cmd_fix))
    _telegram_app.add_handler(CommandHandler("workspace", cmd_workspace))
    _telegram_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    await _telegram_app.initialize()
    await _telegram_app.start()
    await _telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot Telegram démarré")


async def stop_bot() -> None:
    global _telegram_app
    # FIX: guard — stop_bot() sans panic si jamais démarré
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
