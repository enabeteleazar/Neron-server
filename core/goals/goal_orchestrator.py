from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from core.cognitive.critic_engine import get_critic_engine
from core.goals.goal_manager import get_goal_manager
from core.planning import AutonomousPlanner
from core.planning.storage import PlanStorage
from core.task_system.task_executor import get_task_executor
from core.task_system.task_manager import get_task_manager

Notifier = Callable[[str, str], Awaitable[None]]

PLAN_TERMINAL_STATUSES = {
    "plan_finished",
    "refused",
    "blocked_by_risk",
    "failed",
    "superseded",
    "archived",
}

SENSITIVE_ACTIONS = {
    "delete_file",
    "remove_file",
    "rm",
    "unlink",
    "modify_system_config",
    "modify_systemd",
    "restart_systemd",
    "write_secret",
    "read_secret",
    "modify_secret",
    "modify_security",
    "modify_core",
    "apply_destructive_change",
    "destructive_action",
}

SENSITIVE_KEYWORDS = {
    "supprimer",
    "suppression",
    "delete",
    "remove",
    "destructif",
    "destructive",
    "systemd",
    "service systemd",
    "configuration système",
    "system config",
    "secret",
    "secrets",
    "token",
    "tokens",
    "clé ssh",
    "ssh key",
    "api key",
    "sécurité",
    "security",
    "core critique",
}


class GoalOrchestrator:
    """
    Orchestrateur semi-autonome du workflow Goal -> Plan -> Tasks -> Risk -> Execution.

    Il centralise la logique jusque-là répartie entre Telegram, Planner et TaskManager,
    tout en conservant les composants existants et les routes publiques.
    """

    def __init__(
        self,
        planner: AutonomousPlanner | None = None,
        storage: PlanStorage | None = None,
        notifier: Notifier | None = None,
    ) -> None:
        self.goal_manager = get_goal_manager()
        self.planner = planner or AutonomousPlanner()
        self.storage = storage or PlanStorage()
        self.task_manager = get_task_manager()
        self.task_executor = get_task_executor()
        self.critic = get_critic_engine()
        self.notifier = notifier

    async def run_goal(self, objective: str, source: str = "system") -> dict[str, Any]:
        title = objective.strip()
        if not title:
            return {"status": "invalid", "message": "Objectif vide."}

        goal = self.goal_manager.create_goal(
            title=title,
            priority="high" if source == "telegram" else "medium",
            source=source,
            metadata={"orchestrated": True},
        )
        self.goal_manager.update_status(str(goal["id"]), "active")
        goal = self.goal_manager.get_goal(str(goal["id"])) or goal

        plan = self.planner.create_plan(title).to_dict()
        plan.update(
            {
                "goal_id": goal.get("id"),
                "source": f"{source}_goal",
                "status": "pending",
                "approved": False,
                "approval_required": False,
                "orchestrated": True,
            }
        )

        created_tasks = self.task_manager.create_tasks_from_plan(plan)
        plan["tasks_generated"] = True
        plan["generated_task_ids"] = [task.get("id") for task in created_tasks]

        risk = self.critic.evaluate_plan(plan)
        sensitive = self._detect_sensitive_action(plan)
        if sensitive["detected"]:
            risk = {
                **risk,
                "risk_score": max(int(risk.get("risk_score", 0)), 90),
                "risk_level": "critical",
                "execution_allowed": False,
                "sensitive_action_detected": True,
                "sensitive_reasons": sensitive["reasons"],
            }
        plan["risk"] = risk

        decision = self._decide(risk, sensitive["detected"])
        plan["decision"] = decision
        plan["decision_at"] = self._now()

        if decision == "blocked":
            plan["status"] = "blocked_by_risk"
            plan["approval_required"] = False
            plan["error"] = "Exécution bloquée par le CriticEngine."
            self.storage.save(plan)
            await self._notify_blocked(plan)
            return {"status": decision, "goal": goal, "plan": plan, "tasks": created_tasks}

        if decision == "approval_required":
            plan["status"] = "approval_required"
            plan["approval_required"] = True
            self.storage.save(plan)
            await self._notify_approval_required(plan)
            return {"status": decision, "goal": goal, "plan": plan, "tasks": created_tasks}

        plan["approved"] = True
        plan["approval_required"] = False
        plan["approved_by"] = "risk_policy"
        plan["approved_at"] = self._now()
        plan["status"] = "approved"
        self.storage.save(plan)

        execution = await self.execute_plan(plan, approved_by="risk_policy")
        return {"status": execution["status"], "goal": goal, "plan": execution["plan"], "tasks": created_tasks}

    async def execute_approved_plan(self, plan_id: str, approved_by: str = "telegram") -> dict[str, Any]:
        plan = self.find_plan(plan_id)
        if not plan:
            return {"status": "not_found", "error": "Plan introuvable."}

        if plan.get("status") in PLAN_TERMINAL_STATUSES:
            return {"status": "not_executable", "plan": plan, "error": "Plan déjà finalisé."}

        plan["approved"] = True
        plan["approval_required"] = False
        plan["approved_by"] = approved_by
        plan["approved_at"] = self._now()
        plan["status"] = "approved"
        plan["error"] = None

        risk = self.critic.evaluate_plan(plan)
        sensitive = self._detect_sensitive_action(plan)
        if sensitive["detected"]:
            risk = {
                **risk,
                "risk_score": max(int(risk.get("risk_score", 0)), 90),
                "risk_level": "critical",
                "execution_allowed": False,
                "sensitive_action_detected": True,
                "sensitive_reasons": sensitive["reasons"],
            }
        plan["risk"] = risk

        if self._decide(risk, sensitive["detected"]) == "blocked":
            plan["status"] = "blocked_by_risk"
            plan["error"] = "Exécution bloquée par le CriticEngine."
            self.storage.update(plan)
            await self._notify_blocked(plan)
            return {"status": "blocked", "plan": plan, "risk": risk}

        self.storage.update(plan)
        return await self.execute_plan(plan, approved_by=approved_by)

    async def execute_plan(self, plan: dict[str, Any], approved_by: str = "system") -> dict[str, Any]:
        plan_id = str(plan.get("id") or "")
        if not plan_id:
            return {"status": "failed", "plan": plan, "error": "Plan sans identifiant."}

        if plan.get("approved") is not True:
            plan["status"] = "approval_required"
            plan["approval_required"] = True
            self.storage.update(plan)
            return {"status": "approval_required", "plan": plan}

        related_tasks = self._tasks_for_plan(plan_id)
        if not related_tasks:
            related_tasks = self.task_manager.create_tasks_from_plan(plan)
            plan["tasks_generated"] = True
            plan["generated_task_ids"] = [task.get("id") for task in related_tasks]

        plan["status"] = "running"
        plan["execution_started_at"] = self._now()
        plan["executed_by"] = approved_by
        self.storage.update(plan)
        await self._notify_execution_started(plan)

        total = len(related_tasks)
        completed_ids: list[str] = []
        failed_ids: list[str] = []

        for index, task in enumerate(related_tasks, start=1):
            if task.get("status") in {"completed", "skipped"}:
                completed_ids.append(str(task.get("id")))
                continue

            self.task_manager.update_task(str(task["id"]), {"status": "in_progress"})
            current_task = self.task_manager.get_task(str(task["id"])) or task

            try:
                result = self.task_executor.execute(current_task)
                if result.get("status") == "success":
                    updated = self.task_manager.update_task(
                        str(task["id"]),
                        {
                            "status": "completed",
                            "progress": 100,
                            "completed_at": self.task_manager._now(),
                            "result": result,
                            "error": None,
                        },
                    )
                    completed_ids.append(str(task.get("id")))
                    await self._notify_task_done(plan, updated or current_task, index, total)
                else:
                    updated = self.task_manager.update_task(
                        str(task["id"]),
                        {"status": "skipped", "result": result, "progress": 100},
                    )
                    completed_ids.append(str(task.get("id")))
                    await self._notify_task_done(plan, updated or current_task, index, total, skipped=True)
            except Exception as exc:
                failed = self.task_manager.fail_task(str(task["id"]), str(exc))
                failed_ids.append(str(task.get("id")))
                await self._notify_task_failed(plan, failed or current_task, index, total, str(exc))
                plan["status"] = "failed"
                plan["error"] = str(exc)
                plan["failed_task_ids"] = failed_ids
                self.storage.update(plan)
                await self._notify_execution_failed(plan)
                return {"status": "failed", "plan": plan, "error": str(exc)}

        plan["completed_task_ids"] = completed_ids
        plan["failed_task_ids"] = failed_ids
        plan["tasks_completed"] = True
        plan["tasks_completed_at"] = self._now()
        plan["status"] = "tasks_completed"
        self.storage.update(plan)

        plan["status"] = "plan_finished"
        plan["finished_at"] = self._now()
        plan["error"] = None
        self.storage.update(plan)
        self._complete_goal(plan)
        await self._notify_execution_finished(plan)
        return {"status": "plan_finished", "plan": plan}

    def find_plan(self, plan_id_or_prefix: str) -> dict[str, Any] | None:
        wanted = plan_id_or_prefix.strip()
        if not wanted:
            return None

        exact = self.storage.get(wanted)
        if exact:
            return exact

        for candidate in self.storage.history(limit=500):
            plan_id = str(candidate.get("id") or "")
            if plan_id.startswith(wanted):
                return candidate

        return None

    def sync_plan_task_status(self, plan_id: str) -> dict[str, Any] | None:
        plan = self.find_plan(plan_id)
        if not plan:
            return None

        tasks = self._tasks_for_plan(str(plan.get("id")))
        if not tasks:
            return plan

        statuses = {task.get("status") for task in tasks}
        if "failed" in statuses:
            plan["status"] = "failed"
        elif statuses <= {"completed", "skipped"}:
            plan["status"] = "tasks_completed"
            plan["tasks_completed"] = True
            plan["completed_task_ids"] = [task.get("id") for task in tasks]
        elif "in_progress" in statuses:
            plan["status"] = "running"
        elif plan.get("status") not in {"approval_required", "approved", "blocked_by_risk"}:
            plan["status"] = "pending"

        self.storage.update(plan)
        return plan

    def _tasks_for_plan(self, plan_id: str) -> list[dict[str, Any]]:
        return [
            task
            for task in self.task_manager.list_tasks()
            if str(task.get("plan_id") or "") == plan_id
        ]

    def _decide(self, risk: dict[str, Any], sensitive_detected: bool) -> str:
        score = int(risk.get("risk_score") or 0)

        # Blocage uniquement pour risque extrême.
        if score > 95:
            return "blocked"

        # Une action sensible ou un risque très élevé nécessite validation humaine.
        if sensitive_detected or score > 80:
            return "approval_required"

        # Faible, moyen ou élevé contrôlé : Néron exécute automatiquement.
        return "auto_execute"

    def _detect_sensitive_action(self, plan: dict[str, Any]) -> dict[str, Any]:
        reasons: list[str] = []
        searchable = [str(plan.get("goal") or "")]

        for step in plan.get("steps", []):
            action = str(step.get("action") or "").lower()
            if action in SENSITIVE_ACTIONS:
                reasons.append(f"Action sensible détectée : {action}.")
            searchable.extend(
                [
                    str(step.get("title") or ""),
                    str(step.get("description") or ""),
                    action,
                    str(step.get("agent") or ""),
                ]
            )

        text = "\n".join(searchable).lower()
        for keyword in SENSITIVE_KEYWORDS:
            if keyword in text:
                reasons.append(f"Mot-clé sensible détecté : {keyword}.")

        return {"detected": bool(reasons), "reasons": sorted(set(reasons))}

    def _complete_goal(self, plan: dict[str, Any]) -> None:
        goal_id = plan.get("goal_id")
        if goal_id:
            self.goal_manager.update_progress(str(goal_id), 1.0)
            self.goal_manager.update_status(str(goal_id), "completed")

    async def _notify(self, message: str, level: str = "info") -> None:
        if self.notifier:
            await self.notifier(message, level)
            return

        try:
            from core.agents.communication.telegram_agent import send_notification

            await send_notification(message, level=level)
        except Exception:
            return

    async def _notify_approval_required(self, plan: dict[str, Any]) -> None:
        risk = plan.get("risk") or {}
        short_id = str(plan.get("id") or "")[:8]
        await self._notify(
            "⚠ Validation requise\n\n"
            f"Objectif :\n{plan.get('goal')}\n\n"
            f"Risque :\n{risk.get('risk_level', 'unknown')} ({risk.get('risk_score', '?')}/100)\n\n"
            f"Approuver :\n/approve {short_id}\n\n"
            f"Refuser :\n/refuse {short_id}",
            level="warning",
        )

    async def _notify_blocked(self, plan: dict[str, Any]) -> None:
        risk = plan.get("risk") or {}
        reasons = risk.get("sensitive_reasons") or risk.get("risks") or ["Risque critique détecté."]
        await self._notify(
            "🚫 Exécution interdite\n\n"
            f"Objectif :\n{plan.get('goal')}\n\n"
            f"Risque :\n{risk.get('risk_level', 'critical')} ({risk.get('risk_score', '?')}/100)\n\n"
            f"Raison :\n{'; '.join(str(reason) for reason in reasons[:3])}",
            level="error",
        )

    async def _notify_execution_started(self, plan: dict[str, Any]) -> None:
        await self._notify(
            "⚙ Exécution démarrée\n"
            f"Objectif : {plan.get('goal')}",
            level="info",
        )

    async def _notify_task_done(
        self,
        plan: dict[str, Any],
        task: dict[str, Any],
        index: int,
        total: int,
        skipped: bool = False,
    ) -> None:
        icon = "⏭" if skipped else "✅"
        label = "Tâche ignorée" if skipped else "Tâche terminée"
        await self._notify(
            f"{icon} {label} {index}/{total}\n{task.get('title')}",
            level="info",
        )

    async def _notify_task_failed(
        self,
        plan: dict[str, Any],
        task: dict[str, Any],
        index: int,
        total: int,
        error: str,
    ) -> None:
        await self._notify(
            f"❌ Tâche échouée {index}/{total}\n{task.get('title')}\nErreur : {error}",
            level="error",
        )

    async def _notify_execution_finished(self, plan: dict[str, Any]) -> None:
        await self._notify(
            "🏁 Objectif terminé\n\n"
            f"Objectif :\n{plan.get('goal')}\n\n"
            "Résultat :\n"
            "✓ Plan généré\n"
            "✓ Tâches exécutées\n"
            "✓ Risque validé\n"
            "✓ Plan terminé",
            level="info",
        )

    async def _notify_execution_failed(self, plan: dict[str, Any]) -> None:
        await self._notify(
            "❌ Exécution échouée\n"
            f"Objectif : {plan.get('goal')}\n"
            f"Erreur : {plan.get('error')}",
            level="error",
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


def run_async(coro: Awaitable[dict[str, Any]]) -> dict[str, Any]:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    raise RuntimeError("run_async ne peut pas être utilisé dans une boucle asyncio active.")


def get_goal_orchestrator(notifier: Notifier | None = None) -> GoalOrchestrator:
    return GoalOrchestrator(notifier=notifier)
