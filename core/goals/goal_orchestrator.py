from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from core.cognitive.critic_engine import get_critic_engine
from core.agent_factory.build_orchestrator import AgentBuildOrchestrator
from core.events.event import Event
from core.events.event_bus import event_bus
from core.goals.goal_manager import get_goal_manager
from core.planning import AutonomousPlanner
from core.planning.storage import PlanStorage
from core.task_system.task_executor import get_task_executor
from core.task_system.task_manager import get_task_manager

Notifier = Callable[[str, str], Awaitable[None]]

PLAN_TERMINAL_STATUSES = {
    "plan_finished",
    "partial",
    "refused",
    "blocked_by_risk",
    "failed",
    "superseded",
    "archived",
    "partial",
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
    "chmod",
    "rm -rf",
    "shell",
    "exécuter du code",
    "execute code",
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
        agent_build_orchestrator: AgentBuildOrchestrator | None = None,
    ) -> None:
        self.goal_manager = get_goal_manager()
        self.planner = planner or AutonomousPlanner()
        self.storage = storage or PlanStorage()
        self.task_manager = get_task_manager()
        self.task_executor = get_task_executor()
        self.critic = get_critic_engine()
        self.notifier = notifier
        self.agent_build_orchestrator = agent_build_orchestrator or AgentBuildOrchestrator()

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
        await self._publish_flow_event("goal.created", {"goal_id": goal.get("id"), "title": title, "source": source})

        plan = self.planner.create_plan(title).to_dict()
        plan.update(
            {
                "goal_id": goal.get("id"),
                "planner_called": True,
                "source": f"{source}_goal",
                "status": "pending",
                "approved": False,
                "approval_required": False,
                "orchestrated": True,
            }
        )
        await self._publish_flow_event(
            "planner.plan_created",
            {"goal_id": goal.get("id"), "plan_id": plan.get("id"), "steps": len(plan.get("steps", []))},
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
            return self._goal_response(decision, goal, plan, created_tasks)

        if decision == "approval_required":
            plan["status"] = "approval_required"
            plan["approval_required"] = True
            self.storage.save(plan)
            await self._notify_approval_required(plan)
            return self._goal_response(decision, goal, plan, created_tasks)

        plan["approved"] = True
        plan["approval_required"] = False
        plan["approved_by"] = "risk_policy"
        plan["approved_at"] = self._now()
        plan["status"] = "approved"
        self.storage.save(plan)

        if self._is_agent_creation_plan(plan):
            execution = await self.execute_agent_build_plan(plan, approved_by="risk_policy")
            return self._goal_response(execution["status"], goal, execution["plan"], created_tasks)

        execution = await self.execute_plan(plan, approved_by="risk_policy")
        return self._goal_response(execution["status"], goal, execution["plan"], created_tasks)

    async def execute_agent_build_plan(
        self,
        plan: dict[str, Any],
        approved_by: str = "system",
    ) -> dict[str, Any]:
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
        plan["agent_build_orchestrator_called"] = True
        self.storage.update(plan)
        await self._notify_execution_started(plan)

        source_channel = str(plan.get("source") or "api_goal").removesuffix("_goal")
        build_result = await self.agent_build_orchestrator.build_from_request(
            str(plan.get("goal") or ""),
            requested_by=approved_by,
            source_channel=source_channel or "api",
        )
        plan["agent_build_result"] = build_result
        plan["agent_build_status"] = build_result.get("status")
        plan["agent_creator_called"] = True
        self._attach_build_result(plan, build_result)

        if build_result.get("status") != "completed":
            for task in related_tasks:
                self.task_manager.update_task(
                    str(task.get("id")),
                    {
                        "status": "failed",
                        "progress": 100,
                        "result": build_result,
                        "error": build_result.get("response") or "agent_build_failed",
                    },
                )
            plan["status"] = "refused" if build_result.get("status") == "refused" else "failed"
            plan["tasks_completed"] = False
            plan["tasks_completed_at"] = self._now()
            plan["error"] = build_result.get("response") or "Création d'agent échouée."
            plan["execution_summary"] = {
                "completed": 0,
                "skipped": 0,
                "failed": len(related_tasks),
                "total": len(related_tasks),
            }
            self.storage.update(plan)
            if plan["status"] == "refused" and plan.get("goal_id"):
                self.goal_manager.update_status(str(plan.get("goal_id")), "failed")
            await self._notify_execution_failed(plan)
            return {"status": plan["status"], "plan": plan, "error": plan.get("error")}

        completed_ids: list[str] = []
        for task in related_tasks:
            updated = self.task_manager.update_task(
                str(task.get("id")),
                {
                    "status": "completed",
                    "progress": 100,
                    "completed_at": self.task_manager._now(),
                    "result": build_result,
                    "error": None,
                },
            )
            completed_ids.append(str(task.get("id")))
            self._update_plan_step_from_task(plan, updated or task)

        plan["completed_task_ids"] = completed_ids
        plan["skipped_task_ids"] = []
        plan["failed_task_ids"] = []
        plan["tasks_completed"] = True
        plan["tasks_completed_at"] = self._now()
        plan["execution_summary"] = {
            "completed": len(completed_ids),
            "skipped": 0,
            "failed": 0,
            "total": len(related_tasks),
        }
        plan["task_counts"] = dict(plan["execution_summary"])
        plan["status"] = "plan_finished"
        plan["finished_at"] = self._now()
        plan["error"] = None
        self.storage.update(plan)
        self._complete_goal(plan)
        await self._notify_execution_finished(plan)
        return {"status": "plan_finished", "plan": plan}

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
        skipped_ids: list[str] = []
        failed_ids: list[str] = []
        agent_path: str | None = None

        for index, task in enumerate(related_tasks, start=1):
            if task.get("status") == "completed":
                completed_ids.append(str(task.get("id")))
                self._update_plan_step_from_task(plan, task)
                existing_result = task.get("result") or {}
                agent_path = agent_path or existing_result.get("agent_path")
                self._attach_agent_proposal_from_result(plan, existing_result)
                continue

            if task.get("status") == "skipped":
                skipped_ids.append(str(task.get("id")))
                self._update_plan_step_from_task(plan, task)
                continue

            self.task_manager.update_task(str(task["id"]), {"status": "in_progress"})
            current_task = self.task_manager.get_task(str(task["id"])) or task

            try:
                result = self.task_executor.execute(current_task)
                if result.get("status") == "success":
                    agent_path = agent_path or result.get("agent_path")
                    proposal = self._extract_agent_proposal(result)
                    self._attach_agent_proposal_from_result(plan, result)
                    proposal_id = (proposal or {}).get("agent_request_id")
                    if proposal and plan.get("agent_creator_event_published_for") != proposal_id:
                        await self._publish_flow_event(
                            "agent_creator.proposal_created",
                            {
                                "goal_id": plan.get("goal_id"),
                                "plan_id": plan.get("id"),
                                "agent_request_id": proposal_id,
                                "agent_name": proposal.get("agent_name"),
                                "status": proposal.get("status"),
                            },
                        )
                        plan["agent_creator_event_published_for"] = proposal_id
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
                    self._update_plan_step_from_task(plan, updated or current_task)
                    await self._notify_task_done(plan, updated or current_task, index, total)
                elif result.get("status") == "skipped":
                    updated = self.task_manager.update_task(
                        str(task["id"]),
                        {"status": "skipped", "result": result, "progress": 100},
                    )
                    skipped_ids.append(str(task.get("id")))
                    self._update_plan_step_from_task(plan, updated or current_task)
                    await self._notify_task_done(plan, updated or current_task, index, total, skipped=True)
                else:
                    error = result.get("error") or result.get("summary") or "Action échouée."
                    failed = self.task_manager.fail_task(str(task["id"]), str(error))
                    failed_ids.append(str(task.get("id")))
                    self._update_plan_step_from_task(plan, failed or current_task)
                    await self._notify_task_failed(plan, failed or current_task, index, total, str(error))
                    plan["status"] = "failed"
                    plan["error"] = str(error)
                    plan["failed_task_ids"] = failed_ids
                    self._attach_execution_summary(plan, related_tasks, completed_ids, skipped_ids, failed_ids)
                    self.storage.update(plan)
                    await self._notify_execution_failed(plan)
                    return {"status": "failed", "plan": plan, "error": str(error)}
            except Exception as exc:
                failed = self.task_manager.fail_task(str(task["id"]), str(exc))
                failed_ids.append(str(task.get("id")))
                self._update_plan_step_from_task(plan, failed or current_task)
                await self._notify_task_failed(plan, failed or current_task, index, total, str(exc))
                plan["status"] = "failed"
                plan["error"] = str(exc)
                plan["failed_task_ids"] = failed_ids
                self._attach_execution_summary(plan, related_tasks, completed_ids, skipped_ids, failed_ids)
                self.storage.update(plan)
                await self._notify_execution_failed(plan)
                return {"status": "failed", "plan": plan, "error": str(exc)}

        plan["completed_task_ids"] = completed_ids
        plan["skipped_task_ids"] = skipped_ids
        plan["failed_task_ids"] = failed_ids
        plan["task_counts"] = {
            "total": total,
            "completed": len(completed_ids),
            "skipped": len(skipped_ids),
            "failed": len(failed_ids),
        }
        if agent_path:
            plan["agent_path"] = agent_path
            plan["agent_draft"] = {"path": agent_path, "state": "draft_only"}

        creation_actions = {"analyze_agents", "define_agent", "create_skeleton", "check_integration"}
        creation_task_ids = [
            str(task.get("id"))
            for task in related_tasks
            if task.get("action") in creation_actions
        ]
        create_skeleton_tasks = [
            task for task in related_tasks if task.get("action") == "create_skeleton"
        ]
        creation_goal = bool(creation_task_ids)
        creation_skipped = creation_goal and all(
            task_id in skipped_ids for task_id in creation_task_ids
        )
        missing_draft = creation_goal and create_skeleton_tasks and not plan.get("agent_path")

        if failed_ids or creation_skipped or missing_draft or (total and not completed_ids and skipped_ids):
            plan["tasks_completed"] = False
            plan["tasks_completed_at"] = self._now()
            plan["status"] = "failed" if failed_ids or creation_skipped or missing_draft else "partial"
            plan["error"] = self._final_error(plan, creation_skipped, missing_draft)
            self.storage.update(plan)
            await self._notify_execution_failed(plan)
            return {"status": plan["status"], "plan": plan, "error": plan.get("error")}

        plan["tasks_completed"] = True
        plan["tasks_completed_at"] = self._now()
        plan["status"] = "tasks_completed"
        self._attach_execution_summary(plan, related_tasks, completed_ids, skipped_ids, failed_ids)
        self.storage.update(plan)

        if self._requires_agent_draft(plan) and not plan.get("agent_path"):
            plan["status"] = "failed"
            plan["error"] = "Brouillon agent non créé."
            self.storage.update(plan)
            await self._notify_execution_failed(plan)
            return {"status": "failed", "plan": plan, "error": plan["error"]}

        if not completed_ids:
            plan["status"] = "failed"
            plan["error"] = "Aucune tâche exécutée."
            self.storage.update(plan)
            await self._notify_execution_failed(plan)
            return {"status": "failed", "plan": plan, "error": plan["error"]}

        if skipped_ids:
            plan["status"] = "partial"
            plan["partial_at"] = self._now()
            plan["error"] = "Certaines tâches ont été ignorées."
            self.storage.update(plan)
            await self._notify_execution_partial(plan)
            return {"status": "partial", "plan": plan, "error": plan["error"]}

        plan["status"] = "plan_finished"
        plan["finished_at"] = self._now()
        plan["error"] = None
        self.storage.update(plan)
        self._complete_goal(plan)
        await self._notify_execution_finished(plan)
        return {"status": "plan_finished", "plan": plan}

    def _final_error(self, plan: dict[str, Any], creation_skipped: bool, missing_draft: bool) -> str:
        if plan.get("failed_task_ids"):
            return "Une ou plusieurs tâches ont échoué."
        if creation_skipped:
            return "Objectif de création d'agent non exécuté : toutes les tâches importantes ont été ignorées."
        if missing_draft:
            return "Objectif de création d'agent incomplet : aucun brouillon n'a été créé."
        return "Aucune tâche exécutable n'a été terminée."

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

        completed_ids = [str(task.get("id")) for task in tasks if task.get("status") == "completed"]
        skipped_ids = [str(task.get("id")) for task in tasks if task.get("status") == "skipped"]
        failed_ids = [str(task.get("id")) for task in tasks if task.get("status") == "failed"]

        for task in tasks:
            self._update_plan_step_from_task(plan, task)

        self._attach_execution_summary(plan, tasks, completed_ids, skipped_ids, failed_ids)

        statuses = {task.get("status") for task in tasks}
        if failed_ids:
            plan["status"] = "failed"
        elif statuses <= {"completed", "skipped"}:
            completed = [task for task in tasks if task.get("status") == "completed"]
            skipped = [task for task in tasks if task.get("status") == "skipped"]
            creation_actions = {"analyze_agents", "define_agent", "create_skeleton", "check_integration"}
            creation_tasks = [task for task in tasks if task.get("action") in creation_actions]
            all_creation_skipped = bool(creation_tasks) and all(
                task.get("status") == "skipped" for task in creation_tasks
            )
            if all_creation_skipped or (skipped and not completed):
                plan["status"] = "failed" if all_creation_skipped else "partial"
                plan["tasks_completed"] = False
                plan["error"] = "Aucune tâche exécutable n'a été terminée."
            else:
                plan["status"] = "tasks_completed"
                plan["tasks_completed"] = True
            plan["completed_task_ids"] = [task.get("id") for task in completed]
            plan["skipped_task_ids"] = [task.get("id") for task in skipped]
        elif "in_progress" in statuses:
            plan["status"] = "running"
        elif plan.get("status") not in {"approval_required", "approved", "blocked_by_risk"}:
            plan["status"] = "pending"

        self.storage.update(plan)
        return plan

    def _update_plan_step_from_task(self, plan: dict[str, Any], task: dict[str, Any]) -> None:
        task_action = task.get("action")
        task_title = task.get("title")

        for step in plan.get("steps", []):
            if task_action and step.get("action") != task_action:
                continue

            if not task_action and task_title and step.get("title") != task_title:
                continue

            status = task.get("status")
            if status in {"completed", "skipped", "failed", "in_progress"}:
                step["status"] = status

            if "result" in task:
                step["result"] = task.get("result")

            if task.get("error"):
                step["error"] = task.get("error")
            elif status in {"completed", "skipped"}:
                step["error"] = None

            return

    def _attach_execution_summary(
        self,
        plan: dict[str, Any],
        tasks: list[dict[str, Any]],
        completed_ids: list[str],
        skipped_ids: list[str],
        failed_ids: list[str],
    ) -> None:
        plan["completed_task_ids"] = completed_ids
        plan["skipped_task_ids"] = skipped_ids
        plan["failed_task_ids"] = failed_ids
        plan["execution_summary"] = {
            "completed": len(completed_ids),
            "skipped": len(skipped_ids),
            "failed": len(failed_ids),
            "total": len(tasks),
        }

        agent_path = self._find_agent_path(tasks)
        if agent_path:
            plan["agent_path"] = agent_path
            plan["agent_state"] = "draft_only"

        for task in tasks:
            self._attach_agent_proposal_from_result(plan, task.get("result") or {})

    def _find_agent_path(self, tasks: list[dict[str, Any]]) -> str | None:
        for task in tasks:
            result = task.get("result") or {}
            path = result.get("agent_path")

            if not path and isinstance(result.get("result"), dict):
                path = result["result"].get("path")

            if path:
                return self._project_relative_path(str(path))

        return None

    def _attach_agent_proposal_from_result(
        self,
        plan: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        proposal = self._extract_agent_proposal(result)
        if not proposal:
            return

        plan["agent_creator_called"] = True
        plan["agent_creation_proposal"] = proposal
        plan["agent_request_id"] = proposal.get("agent_request_id")
        plan["agent_proposal_status"] = proposal.get("status")
        plan["applied_to_core"] = False

    def _attach_build_result(self, plan: dict[str, Any], build_result: dict[str, Any]) -> None:
        project = build_result.get("project") or {}
        spec = build_result.get("spec") or {}
        result = project.get("result") or {}
        created_files = list(project.get("created_files") or [])
        agent_name = (
            project.get("registered_agent")
            or result.get("agent")
            or spec.get("name")
        )
        runtime_reload = (
            build_result.get("runtime_reload")
            or result.get("runtime_reload")
            or ((result.get("verification") or {}).get("runtime_reload") if isinstance(result.get("verification"), dict) else None)
        )
        test_results = project.get("test_results") or []
        tests_ok = bool(test_results) and all(item.get("returncode") == 0 for item in test_results)
        agent_path = next(
            (path for path in created_files if str(path).endswith(f"{agent_name}.py") and "core/agents/generated/" in str(path)),
            None,
        )

        if agent_name:
            plan["agent_name"] = agent_name
            plan["registered_agent"] = agent_name
            plan["agent_request_id"] = str(project.get("project_id") or agent_name)
        if agent_path:
            plan["agent_path"] = agent_path
            plan["agent_state"] = "registered"
        plan["created_files"] = created_files
        plan["build_project_id"] = project.get("project_id")
        plan["registry_status"] = project.get("registry_status")
        plan["runtime_reload"] = runtime_reload
        plan["tests_ok"] = tests_ok
        plan["applied_to_core"] = build_result.get("status") == "completed" and bool(agent_name)
        plan["human_validation_required"] = False
        plan["agent_creation_proposal"] = {
            "agent_request_id": plan.get("agent_request_id"),
            "agent_name": agent_name,
            "goal": spec.get("goal") or plan.get("goal"),
            "required_capabilities": spec.get("capabilities") or [],
            "status": "auto_applied" if build_result.get("status") == "completed" else build_result.get("status"),
            "human_validation_required": False,
            "code_execution_allowed": True,
            "applied_to_core": plan["applied_to_core"],
            "created_from_goal_id": plan.get("goal_id"),
            "created_from_plan_id": plan.get("id"),
        }
        plan["agent_proposal_status"] = plan["agent_creation_proposal"]["status"]

    def _extract_agent_proposal(self, result: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(result, dict):
            return None

        direct = result.get("agent_creation_proposal") or result.get("proposal")
        if isinstance(direct, dict):
            return direct

        nested = result.get("result")
        if isinstance(nested, dict):
            proposal = nested.get("agent_creation_proposal") or nested.get("proposal")
            if isinstance(proposal, dict):
                return proposal

        return None

    def _project_relative_path(self, path: str) -> str:
        try:
            return str(Path(path).resolve().relative_to(Path("/etc/neron").resolve()))
        except ValueError:
            return path

    def _requires_agent_draft(self, plan: dict[str, Any]) -> bool:
        return any(
            step.get("agent") == "agent_creator" or step.get("action") == "create_skeleton"
            for step in plan.get("steps", [])
        )

    def _is_agent_creation_plan(self, plan: dict[str, Any]) -> bool:
        return any(
            step.get("agent") == "agent_creator"
            or step.get("action") in {"define_agent", "create_skeleton"}
            for step in plan.get("steps", [])
        )

    def _goal_response(
        self,
        status: str,
        goal: dict[str, Any],
        plan: dict[str, Any],
        tasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        proposal = plan.get("agent_creation_proposal")
        return {
            "status": status,
            "goal": goal,
            "goal_id": goal.get("id"),
            "planner_called": bool(plan.get("planner_called") or plan.get("id")),
            "plan_id": plan.get("id"),
            "plan": plan,
            "agent_creator_called": self._agent_creator_called(plan, tasks),
            "agent_request_id": plan.get("agent_request_id")
            or (proposal or {}).get("agent_request_id"),
            "proposal": proposal,
            "tasks": tasks,
        }

    def _agent_creator_called(
        self,
        plan: dict[str, Any],
        tasks: list[dict[str, Any]],
    ) -> bool:
        if plan.get("agent_creator_called") is True or plan.get("agent_creation_proposal"):
            return True
        if any(step.get("agent") == "agent_creator" for step in plan.get("steps", [])):
            return any(task.get("status") == "completed" for task in tasks)
        return False

    async def _publish_flow_event(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            await event_bus.publish(Event(type=event_type, source="goal_orchestrator", payload=payload))
        except Exception:
            return

    def _tasks_for_plan(self, plan_id: str) -> list[dict[str, Any]]:
        return [
            task
            for task in self.task_manager.list_tasks()
            if str(task.get("plan_id") or "") == plan_id
        ]

    def _decide(self, risk: dict[str, Any], sensitive_detected: bool) -> str:
        score = int(risk.get("risk_score") or 0)

        if sensitive_detected or score > 95:
            return "blocked"
        if score > 80:
            return "approval_required"
        if risk.get("execution_allowed") is True and score <= 50:
            return "auto_execute"
        return "approval_required"

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
            self._format_execution_report(plan, "🏁 Objectif terminé"),
            level="info",
        )

    async def _notify_execution_partial(self, plan: dict[str, Any]) -> None:
        await self._notify(
            self._format_execution_report(plan, "⚠ Objectif partiel"),
            level="warning",
        )

    async def _notify_execution_failed(self, plan: dict[str, Any]) -> None:
        await self._notify(
            self._format_execution_report(plan, "❌ Exécution échouée"),
            level="error",
        )

    def _format_execution_report(self, plan: dict[str, Any], title: str) -> str:
        risk = plan.get("risk") or {}
        summary = plan.get("execution_summary") or {}
        agent_path = plan.get("agent_path")
        proposal = plan.get("agent_creation_proposal") or {}
        result_lines = [
            "✓ Plan généré",
            "✓ Risque validé",
        ]

        if agent_path:
            if plan.get("agent_state") == "registered":
                result_lines.append("✓ Agent enregistré")
            else:
                result_lines.append("✓ Brouillon créé")
        if proposal:
            result_lines.append("✓ Proposition d'agent créée")
        if plan.get("tests_ok") is True:
            result_lines.append("✓ Tests OK")
        if (plan.get("runtime_reload") or {}).get("ok") is True:
            result_lines.append("✓ Runtime rechargé")

        if plan.get("status") == "partial":
            result_lines.append("⚠ Certaines tâches ignorées")

        if plan.get("status") == "failed":
            result_lines.append("✗ Exécution incomplète")

        lines = [
            title,
            "",
            "Objectif :",
            str(plan.get("goal")),
            "",
            f"Plan ID : {plan.get('id')}",
            f"Risque : {risk.get('risk_level', 'unknown')} ({risk.get('risk_score', '?')}/100)",
            "",
            "Résultat :",
            *result_lines,
            "",
            "Tâches :",
            f"completed : {summary.get('completed', 0)}",
            f"skipped : {summary.get('skipped', 0)}",
            f"failed : {summary.get('failed', 0)}",
        ]

        if agent_path:
            lines.extend(
                [
                    "",
                    "Agent :",
                    str(agent_path),
                    "",
                    "État :",
                    str(plan.get("agent_state") or "draft_only"),
                ]
            )

        if plan.get("registered_agent"):
            lines.extend(
                [
                    "",
                    "Agent enregistré :",
                    str(plan.get("registered_agent")),
                ]
            )

        if proposal:
            lines.extend(
                [
                    "",
                    "Proposition :",
                    str(proposal.get("agent_name")),
                    "",
                    "État :",
                    str(proposal.get("status")),
                ]
            )

        if plan.get("error"):
            lines.extend(["", "Erreur :", str(plan.get("error"))])

        return "\n".join(lines)

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
