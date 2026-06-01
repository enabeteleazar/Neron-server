# core/agents/communication/telegram_agent.py
# Néron Core - Bot Telegram intégré
# v2.1 — Telegram passe par /input/text pour utiliser le vrai routage agents

from __future__ import annotations

import asyncio
import os
import time
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone

from core.planning.storage import PlanStorage
from core.planning import AutonomousPlanner
from core.task_system.task_manager import get_task_manager
from core.planning.executor import PlanExecutor
from core.task_system.task_manager import get_task_manager
from core.cognitive.critic_engine import get_critic_engine
from core.goals.goal_orchestrator import get_goal_orchestrator
from core.code_awareness.analyzer import analyze_file
from core.code_awareness.architecture_mapper import map_architecture
from core.code_awareness.reader import read_file
from core.code_awareness.scanner import scan_project
from core.code_awareness.searcher import search_code
from core.code_awareness.security import CodeAwarenessSecurityError
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
from core.agents.automation.watchdog_agent import get_health_score, get_status
from core.config import settings
from core.agents.communication.twilio_agent import call as twilio_call

logger = get_logger("telegram_agent")

TELEGRAM_TOKEN = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID
NERON_CORE_URL = f"http://127.0.0.1:{settings.SERVER_PORT}"
NERON_API_KEY = settings.API_KEY
ALLOWED_CHAT_IDS = set(filter(None, settings.TELEGRAM_CHAT_ID.split(",")))

_WORKSPACE = Path(
    os.getenv(
        "NERON_WORKSPACE",
        str(Path(__file__).parent.parent.parent / "workspace"),
    )
)

_agents: dict = {}
_telegram_app: Application | None = None


def set_agents(agents: dict) -> None:
    global _agents
    _agents = agents


def is_authorized(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return str(update.message.chat_id) in ALLOWED_CHAT_IDS


async def unauthorized(update: Update) -> None:
    await update.message.reply_text("⛔ Accès non autorisé")
    logger.warning("Accès refusé: chat_id=%s", update.message.chat_id)


def _normalize(text: str) -> str:
    n = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in n if unicodedata.category(c) != "Mn")


async def _post_text(client: httpx.AsyncClient, text: str) -> dict:
    resp = await client.post(
        f"{NERON_CORE_URL}/input/text",
        json={"text": text},
        headers={"X-API-Key": NERON_API_KEY},
    )
    resp.raise_for_status()
    return resp.json()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    await update.message.reply_text(
        "👋 Bonjour ! Je suis <b>Néron</b>, ton assistant IA personnel.\n"
        "Tape /help pour voir les commandes disponibles.",
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    await update.message.reply_text(
        "🤖 <b>Néron — Commandes disponibles</b>\n\n"
        "💬 <b>Conversation</b>\n"
        "  Envoyez n'importe quel message pour parler à Néron\n\n"
        "🧪 <b>Diagnostics directs</b>\n"
        "  ports ouverts\n"
        "  liste les services actifs\n"
        "  statut système\n\n"
        "💻 <b>Code</b>\n"
        "  /fix &lt;fichier.py&gt; — améliore un fichier\n"
        "  /review — auto-review du code\n"
        "  /run &lt;fichier.py&gt; — exécute un script du workspace\n"
        "  /workspace — liste les fichiers du workspace\n\n"
        "🧭 <b>Code Awareness</b>\n"
        "  /code_map — carte simplifiée du dépôt\n"
        "  /code_search &lt;terme&gt; — recherche dans le code\n"
        "  /code_read &lt;fichier&gt; — lecture sécurisée\n"
        "  /code_analyze &lt;fichier&gt; — analyse AST\n"
        "  /architecture — vue globale\n\n"
        "🧠 <b>Mémoire</b>\n"
        "  /memory — 5 derniers échanges\n\n"
        "🏠 <b>Home Assistant</b>\n"
        "  /ha_reload — recharge les entités HA\n\n"
        "📊 <b>Système</b>\n"
        "  /status — CPU, RAM, disque, uptime\n\n"
        "📞 <b>Téléphonie</b>\n"
        "  /call [message] — appel vocal via Twilio\n\n"
        "❓ /help — cette aide",
        parse_mode="HTML",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    try:
        st = get_status()
        if "error" in st:
            await update.message.reply_text(f"❌ Erreur système : {st['error']}")
            return

        uptime_min = st.get("uptime_s", 0) // 60
        health = get_health_score()
        score = health.get("score", "N/A")

        from core.modules.scheduler import get_jobs

        jobs = get_jobs()
        jobs_text = "\n".join(
            f"  • {j['name']} — {j['next_run']}" for j in jobs
        ) or "  Aucune"

        await update.message.reply_text(
            f"📊 <b>État Néron</b>\n\n"
            f"🖥 CPU     : {st.get('cpu_pct', '?')}%\n"
            f"💾 RAM     : {st.get('ram_pct', '?')}% ({st.get('ram_used_mb', '?')} MB)\n"
            f"💿 Disque  : {st.get('disk_pct', '?')}%\n"
            f"🧠 Process : {st.get('process_ram_mb', '?')} MB\n"
            f"⏱ Uptime  : {uptime_min} min\n"
            f"❤ Santé   : {score}/100\n\n"
            f"📅 <b>Tâches planifiées</b>\n{jobs_text}",
            parse_mode="HTML",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {e}")


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


async def cmd_ha_reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    ha_agent = _agents.get("ha")
    if not ha_agent:
        await update.message.reply_text("❌ Agent Home Assistant non disponible")
        return

    sent = await update.message.reply_text("🔄 Rechargement des entités HA...")

    try:
        count = await ha_agent.reload()
        await sent.edit_text(f"✅ {count} entités HA rechargées")
    except Exception as e:
        await sent.edit_text(f"❌ Erreur HA : {e}")


async def cmd_call(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    if not settings.TWILIO_ENABLED:
        await update.message.reply_text("❌ Twilio non activé (TWILIO_ENABLED=false)")
        return

    message = " ".join(context.args) if context.args else "Appel depuis Néron."
    sent = await update.message.reply_text("📞 Appel en cours...")

    try:
        result = twilio_call(message)
        await sent.edit_text(f"✅ Appel passé : {result}")
    except Exception as e:
        await sent.edit_text(f"❌ Erreur appel : {e}")


async def cmd_workspace(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    try:
        if not _WORKSPACE.exists():
            await update.message.reply_text(f"📁 Workspace vide ou inexistant : {_WORKSPACE}")
            return

        files = sorted(_WORKSPACE.rglob("*.py"))[:30]

        if not files:
            await update.message.reply_text("📁 Aucun fichier .py dans le workspace")
            return

        lines = [f"📁 <b>Workspace</b> ({len(files)} fichiers)\n"]
        for f in files:
            lines.append(f"  • {f.relative_to(_WORKSPACE)}")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur workspace : {e}")


def _telegram_limit(text: str, limit: int = 3900) -> str:
    if len(text) <= limit:
        return text

    return text[: limit - 20].rstrip() + "\n…"


def _tree_lines(node: dict, depth: int = 0, max_lines: int = 45) -> list[str]:
    lines: list[str] = []
    prefix = "  " * depth
    name = node.get("name") or node.get("path") or "?"

    if depth > 0:
        lines.append(f"{prefix}- {name}")

    for child in node.get("children", []):
        if len(lines) >= max_lines:
            break
        lines.extend(_tree_lines(child, depth + 1, max_lines=max_lines - len(lines)))

    return lines[:max_lines]


async def cmd_code_map(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    scan = scan_project(max_depth=2)
    lines = [
        "🧭 Code Awareness",
        "",
        f"Fichiers : {scan.get('files')}",
        f"Modules Python : {scan.get('modules')}",
        "",
        "Arborescence :",
        *_tree_lines(scan.get("tree", {})),
    ]
    await update.message.reply_text(_telegram_limit("\n".join(lines)))


async def cmd_code_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    query = " ".join(context.args).strip()
    if not query:
        return await update.message.reply_text("Usage : /code_search <terme>")

    result = search_code(query, max_results=12)
    lines = [f"🔎 Recherche : {query}", f"Résultats : {result.get('count', 0)}", ""]

    for item in result.get("results", []):
        lines.append(f"{item['file']}:{item['line']}")
        lines.append(f"  {item['excerpt']}")

    await update.message.reply_text(_telegram_limit("\n".join(lines)))


async def cmd_code_read(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    if not context.args:
        return await update.message.reply_text("Usage : /code_read <fichier>")

    try:
        result = read_file(context.args[0], max_lines=80)
    except (CodeAwarenessSecurityError, FileNotFoundError, IsADirectoryError) as exc:
        return await update.message.reply_text(f"❌ Lecture refusée : {exc}")

    header = (
        f"📄 {result['path']}\n"
        f"Lignes : {result['start_line']}-{result['end_line']} / {result['lines']}\n"
        f"Tronqué : {result['truncated']}\n\n"
    )
    await update.message.reply_text(_telegram_limit(header + result["content"]))


async def cmd_code_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    if not context.args:
        return await update.message.reply_text("Usage : /code_analyze <fichier.py>")

    try:
        result = analyze_file(context.args[0])
    except (CodeAwarenessSecurityError, FileNotFoundError, IsADirectoryError) as exc:
        return await update.message.reply_text(f"❌ Analyse refusée : {exc}")

    classes = ", ".join(item["name"] for item in result.get("classes", [])[:8]) or "aucune"
    functions = ", ".join(item["name"] for item in result.get("functions", [])[:12]) or "aucune"
    deps = ", ".join(result.get("dependencies", [])[:10]) or "aucune"
    routes = [
        f"{route.get('decorators', ['route'])[0]} {route.get('path')} -> {route.get('function')}"
        for route in result.get("routes", [])[:8]
    ]

    lines = [
        f"🧩 Analyse : {result.get('path')}",
        "",
        f"Responsabilité : {result.get('responsibility')}",
        f"Classes : {classes}",
        f"Fonctions : {functions}",
        f"Dépendances : {deps}",
    ]
    if routes:
        lines.extend(["Routes :", *routes])

    await update.message.reply_text(_telegram_limit("\n".join(lines)))


async def cmd_architecture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    architecture = map_architecture()
    summary = architecture.get("summary", {})
    lines = [
        "🏛 Architecture Néron",
        "",
        f"Fichiers : {summary.get('files')}",
        f"Modules : {summary.get('modules')}",
        "",
        "Domaines :",
    ]

    for group in architecture.get("groups", []):
        lines.append(f"- {group['name']} : {group['files']} fichiers")

    lines.append("")
    lines.append("Flux clés :")
    for flow in architecture.get("key_flows", []):
        lines.append(" -> ".join(flow))

    await update.message.reply_text(_telegram_limit("\n".join(lines)))


async def cmd_fix(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    if not context.args:
        await update.message.reply_text("Usage : /fix <fichier.py>")
        return

    filename = context.args[0]
    sent = await update.message.reply_text(f"🔧 Analyse de {filename}...")

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            data = await _post_text(client, f"améliore et corrige le fichier {filename}")
            await sent.edit_text(data.get("response", "❌ Pas de réponse")[:4096])
    except Exception as e:
        await sent.edit_text(f"❌ Erreur fix : {e}")


async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    sent = await update.message.reply_text("🔍 Auto-review en cours...")

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            data = await _post_text(client, "lance un auto-review complet du code")
            await sent.edit_text(data.get("response", "❌ Pas de réponse")[:4096])
    except Exception as e:
        await sent.edit_text(f"❌ Erreur review : {e}")


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    if not context.args:
        await update.message.reply_text("Usage : /run <fichier.py>")
        return

    filename = context.args[0]
    target = _WORKSPACE / filename

    if not target.exists():
        await update.message.reply_text(f"❌ Fichier introuvable : {filename}")
        return

    sent = await update.message.reply_text(f"▶ Exécution de {filename}...")

    try:
        proc = await asyncio.create_subprocess_exec(
            "python3",
            str(target),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = stdout.decode("utf-8", errors="replace")[:3000] or "(aucune sortie)"
        await sent.edit_text(f"<pre>{output}</pre>", parse_mode="HTML")
    except asyncio.TimeoutError:
        await sent.edit_text("⏱ Timeout — script interrompu après 30s")
    except Exception as e:
        await sent.edit_text(f"❌ Erreur exécution : {e}")




async def cmd_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    if not context.args:
        return await update.message.reply_text("Usage : /goal <objectif>")

    title = " ".join(context.args).strip()

    if not title:
        return await update.message.reply_text("Usage : /goal <objectif>")

    orchestrator = get_goal_orchestrator()
    result = await orchestrator.run_goal(title, source="telegram")

    plan = result.get("plan", {})
    risk = plan.get("risk", {})
    short_id = str(plan.get("id") or "")[:8]
    status = result.get("status")

    if status == "plan_finished":
        proposal = plan.get("agent_creation_proposal") or {}
        lines = [
            "✅ Objectif reçu",
            "🧠 Plan généré",
            "⚙ Exécution automatique autorisée",
            "🏁 Objectif terminé",
            "",
            f"ID plan : {short_id}",
            f"Risque : {risk.get('risk_level', 'low')} ({risk.get('risk_score', '?')}/100)",
        ]
        if proposal:
            lines.extend(
                [
                    "",
                    f"Proposition : {proposal.get('agent_name')}",
                    f"État : {proposal.get('status')}",
                ]
            )
        await update.message.reply_text("\n".join(lines))
        return

    if status in {"partial", "failed"}:
        await update.message.reply_text(
            "✅ Objectif reçu\n"
            "🧠 Plan généré\n"
            "📄 Rapport d'exécution envoyé\n\n"
            f"ID plan : {short_id}\n"
            f"Statut : {status}"
        )
        return

    if status == "approval_required":
        return

    if status == "blocked":
        await update.message.reply_text(
            "✅ Objectif reçu\n"
            "🧠 Plan généré\n"
            "🚫 Exécution bloquée par le CriticEngine\n\n"
            f"ID plan : {short_id}\n"
            f"Risque : {risk.get('risk_level', 'critical')} ({risk.get('risk_score', '?')}/100)"
        )
        return

    await update.message.reply_text(
        f"✅ Objectif reçu\n🧠 Plan généré\nStatut : {status}\nID plan : {short_id}"
    )


async def cmd_goal_active(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    path = Path("/etc/neron/data/goals_state.json")

    if not path.exists():
        return await update.message.reply_text("Aucun objectif actif trouvé.")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return await update.message.reply_text("Erreur lecture GoalSystem.")

    active_id = data.get("active_goal_id")

    for goal in data.get("goals", []):
        if goal.get("id") == active_id or goal.get("status") == "active":
            return await update.message.reply_text(
                f"🎯 Objectif actif\n\nID : {goal.get('id')}\nTitre : {goal.get('title')}\nPriorité : {goal.get('priority')}"
            )

    await update.message.reply_text("Aucun objectif actif trouvé.")

async def cmd_ready(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    storage = PlanStorage()
    ready = [
        plan
        for plan in storage.history(limit=200)
        if plan.get("status") == "approval_required"
        and plan.get("approval_required") is True
        and plan.get("approved") is not True
    ]

    if not ready:
        return await update.message.reply_text("✅ Aucun plan en attente d'approbation.")

    lines = ["🧠 Plans prêts à approbation", ""]

    for plan in ready[:5]:
        plan_id = str(plan.get("id"))
        short_id = plan_id[:8]
        risk = plan.get("risk", {})
        lines.extend([
            f"ID : {short_id}",
            f"Objectif : {plan.get('goal')}",
            f"Risque : {risk.get('risk_level', 'unknown')} ({risk.get('risk_score', '?')}/100)",
            f"Approuver : /approve {short_id}",
            f"Refuser : /refuse {short_id}",
            "",
        ])

    await update.message.reply_text("\n".join(lines)[:4096])


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    if not context.args:
        return await update.message.reply_text("Usage : /approve <plan_id>")

    wanted = context.args[0].strip()
    orchestrator = get_goal_orchestrator()
    plan = orchestrator.find_plan(wanted)

    if not plan:
        return await update.message.reply_text("❌ Plan introuvable.")

    await update.message.reply_text(
        f"✅ Plan approuvé : {str(plan.get('id'))[:8]}\n"
        f"⚙ Exécution contrôlée démarrée\nObjectif : {plan.get('goal')}"
    )

    result = await orchestrator.execute_approved_plan(wanted, approved_by="telegram")
    updated = result.get("plan", plan)
    status = result.get("status")

    if status == "plan_finished":
        return await update.message.reply_text(
            f"📄 Rapport final envoyé\n\nID : {str(updated.get('id'))[:8]}\nObjectif : {updated.get('goal')}"
        )

    if status in {"partial", "failed"}:
        return await update.message.reply_text(
            f"📄 Rapport d'exécution envoyé\n\n"
            f"ID : {str(updated.get('id'))[:8]}\n"
            f"Statut : {status}"
        )

    if status == "blocked":
        risk = updated.get("risk", {})
        return await update.message.reply_text(
            f"🚫 Exécution interdite\n\nObjectif : {updated.get('goal')}\n"
            f"Risque : {risk.get('risk_level', 'critical')} ({risk.get('risk_score', '?')}/100)"
        )

    return await update.message.reply_text(
        f"❌ Exécution non terminée\nStatut : {status}\nErreur : {result.get('error') or updated.get('error')}"
    )


async def cmd_refuse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    if not context.args:
        return await update.message.reply_text("Usage : /refuse <plan_id>")

    wanted = context.args[0].strip()
    storage = PlanStorage()

    plan = None
    for candidate in storage.history(limit=500):
        plan_id = str(candidate.get("id"))
        if plan_id == wanted or plan_id.startswith(wanted):
            plan = candidate
            break

    if not plan:
        return await update.message.reply_text("❌ Plan introuvable.")

    plan["approved"] = False
    plan["approval_required"] = False
    plan["refused_at"] = datetime.now(timezone.utc).isoformat()
    plan["refused_by"] = "telegram"
    plan["status"] = "refused"
    plan["error"] = "Plan refusé via Telegram."
    storage.update(plan)

    await update.message.reply_text(
        f"🚫 Plan refusé : {str(plan.get('id'))[:8]}\nObjectif : {plan.get('goal')}"
    )


def _format_plans_message(plans: list[dict], title: str) -> str:
    if not plans:
        return "Aucun plan trouvé."

    lines = [title, ""]

    for plan in plans[:10]:
        plan_id = str(plan.get("id"))[:8]
        lines.extend([
            f"ID : {plan_id}",
            f"Objectif : {plan.get('goal')}",
            f"Statut : {plan.get('status')}",
            f"Approuvé : {plan.get('approved')}",
            "",
        ])

    return "\n".join(lines)[:4096]


async def cmd_plans(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    storage = PlanStorage()
    plans = [
        plan
        for plan in storage.history(limit=50)
        if plan.get("status") not in {"superseded", "plan_finished", "archived", "failed", "done"}
    ]

    await update.message.reply_text(
        _format_plans_message(plans, "📋 Plans actifs / utiles")
    )


async def cmd_plans_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    storage = PlanStorage()
    plans = storage.history(limit=20)

    await update.message.reply_text(
        _format_plans_message(plans, "📚 Tous les derniers plans")
    )


async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    manager = get_task_manager()
    tasks = manager.list_active_tasks()

    if not tasks:
        return await update.message.reply_text("✅ Aucune tâche active.")

    lines = ["🧩 Tâches actives", ""]

    for task in tasks[:10]:
        lines.extend([
            f"- {task.get('title')}",
            f"  Source : {task.get('source')}",
            f"  Statut : {task.get('status')}",
            "",
        ])

    await update.message.reply_text("\n".join(lines)[:4096])


async def cmd_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    if not context.args:
        return await update.message.reply_text("Usage : /execute <plan_id>")

    wanted = context.args[0].strip()
    orchestrator = get_goal_orchestrator()
    plan = orchestrator.find_plan(wanted)

    if not plan:
        return await update.message.reply_text("❌ Plan introuvable.")

    if plan.get("approved") is not True:
        return await update.message.reply_text(
            f"⛔ Plan non approuvé. Utilise d'abord : /approve {str(plan.get('id'))[:8]}"
        )

    result = await orchestrator.execute_plan(plan, approved_by="telegram")
    updated = result.get("plan", plan)
    status = result.get("status")

    if status == "plan_finished":
        await update.message.reply_text(
            f"✅ Plan exécuté\n📄 Rapport final envoyé\n\nID : {str(updated.get('id'))[:8]}\nObjectif : {updated.get('goal')}"
        )
    elif status in {"partial", "failed"}:
        await update.message.reply_text(
            f"📄 Rapport d'exécution envoyé\n\n"
            f"ID : {str(updated.get('id'))[:8]}\n"
            f"Statut : {status}"
        )
    else:
        await update.message.reply_text(
            f"⚠ Exécution terminée avec statut : {status}\n\n"
            f"ID : {str(updated.get('id'))[:8]}\nObjectif : {updated.get('goal')}\n"
            f"Erreur : {result.get('error') or updated.get('error')}"
        )


async def cmd_plan_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    storage = PlanStorage()
    plans = [
        plan
        for plan in storage.history(limit=50)
        if plan.get("status") in {"plan_finished", "superseded", "archived", "failed", "refused", "blocked_by_risk", "done"}
    ]

    await update.message.reply_text(
        _format_plans_message(plans, "📚 Historique des plans")
    )


async def cmd_archive_done_plans(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    storage = PlanStorage()
    archived = 0

    for plan in storage.history(limit=1000):
        if plan.get("status") == "plan_finished":
            plan["status"] = "archived"
            plan["archived_by"] = "telegram"
            storage.update(plan)
            archived += 1

    await update.message.reply_text(
        f"📦 Plans archivés : {archived}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await unauthorized(update)

    try:
        import server.core.agents.watchdog_agent as _wdog_mod

        _wdog_mod._last_conversation = time.monotonic()
    except Exception:
        pass

    user_message = update.message.text
    await update.message.chat.send_action("typing")
    sent = await update.message.reply_text("⏳ Néron réfléchit...")

    q = _normalize(user_message)
    is_code = any(_normalize(kw) in q for kw in CODE_KEYWORDS)

    try:
        async with httpx.AsyncClient(timeout=600.0 if is_code else 300.0) as client:
            data = await _post_text(client, user_message)
            response = data.get("response", "❌ Pas de réponse")
            await sent.edit_text(response[:4096], parse_mode=None)

    except Exception as e:
        logger.exception("handle_message error : %s", e)
        await sent.edit_text(f"❌ Erreur: {e}")


async def send_notification(message: str, level: str = "info") -> None:
    if not _telegram_app or not TELEGRAM_CHAT_ID:
        return

    icons = {"info": "ℹ", "warning": "⚠", "alert": "🔴", "error": "❌"}
    icon = icons.get(level, "📢")

    try:
        await _telegram_app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"{icon} {message}",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Erreur notification Telegram : %s", e)


async def start_bot() -> None:
    global _telegram_app

    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN manquant — bot désactivé")
        return

    _telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    _telegram_app.add_handler(CommandHandler("start", cmd_start))
    _telegram_app.add_handler(CommandHandler("help", cmd_help))
    _telegram_app.add_handler(CommandHandler("status", cmd_status))
    _telegram_app.add_handler(CommandHandler("memory", cmd_memory))
    _telegram_app.add_handler(CommandHandler("ha_reload", cmd_ha_reload))
    _telegram_app.add_handler(CommandHandler("call", cmd_call))
    _telegram_app.add_handler(CommandHandler("workspace", cmd_workspace))
    _telegram_app.add_handler(CommandHandler("code_map", cmd_code_map))
    _telegram_app.add_handler(CommandHandler("code_search", cmd_code_search))
    _telegram_app.add_handler(CommandHandler("code_read", cmd_code_read))
    _telegram_app.add_handler(CommandHandler("code_analyze", cmd_code_analyze))
    _telegram_app.add_handler(CommandHandler("architecture", cmd_architecture))
    _telegram_app.add_handler(CommandHandler("fix", cmd_fix))
    _telegram_app.add_handler(CommandHandler("review", cmd_review))
    _telegram_app.add_handler(CommandHandler("run", cmd_run))
    _telegram_app.add_handler(CommandHandler("goal", cmd_goal))
    _telegram_app.add_handler(CommandHandler("goal_active", cmd_goal_active))
    _telegram_app.add_handler(CommandHandler("ready", cmd_ready))
    _telegram_app.add_handler(CommandHandler("approve", cmd_approve))
    _telegram_app.add_handler(CommandHandler("refuse", cmd_refuse))
    _telegram_app.add_handler(CommandHandler("plans", cmd_plans))
    _telegram_app.add_handler(CommandHandler("plans_all", cmd_plans_all))
    _telegram_app.add_handler(CommandHandler("plan_history", cmd_plan_history))
    _telegram_app.add_handler(CommandHandler("archive_done_plans", cmd_archive_done_plans))
    _telegram_app.add_handler(CommandHandler("tasks", cmd_tasks))
    _telegram_app.add_handler(CommandHandler("execute", cmd_execute))
    _telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await _telegram_app.initialize()
    await _telegram_app.start()

    try:
        await _telegram_app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        logger.info("Bot Telegram démarré — commandes enregistrées")
    except Exception as e:
        try:
            import telegram as _telegram_mod

            if isinstance(e, _telegram_mod.error.Conflict):
                logger.warning("Telegram polling conflict: une autre instance est active; polling ignoré")
                return
        except Exception:
            pass

        logger.exception("Erreur lors demarrage du polling Telegram: %s", e)
        raise


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
