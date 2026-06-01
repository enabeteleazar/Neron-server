from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.cognitive.critic_engine import get_critic_engine
from core.planning.executor import PlanExecutor
from core.planning.storage import PlanStorage


AGENT_CREATOR_ACTIONS = {
    "analyze_agents",
    "define_agent",
    "create_skeleton",
    "check_integration",
}


class TaskExecutor:
    def __init__(
        self,
        plan_executor: PlanExecutor | None = None,
        storage: PlanStorage | None = None,
    ) -> None:
        self.plan_executor = plan_executor or PlanExecutor()
        self.storage = storage or PlanStorage()

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        agent = task.get("agent")

        if action in AGENT_CREATOR_ACTIONS:
            return self._execute_agent_creator_action(task)

        if action == "analyze_goal":
            return {
                "status": "success",
                "agent": agent,
                "action": action,
                "summary": "Objectif analysé.",
                "goal": task.get("goal"),
            }

        if action == "decompose_goal":
            return {
                "status": "success",
                "agent": agent,
                "action": action,
                "summary": "Objectif décomposé en étapes via Planner.",
                "goal": task.get("goal"),
            }

        if action == "evaluate_plan":
            critic = get_critic_engine()

            plan_id = task.get("plan_id")
            plan = self.storage.get(str(plan_id)) if plan_id else None

            if not plan:
                plan = {
                    "id": task.get("plan_id"),
                    "goal": task.get("goal"),
                    "steps": [],
                    "approved": False,
                }

            risk = critic.evaluate_plan(plan)

            if plan_id and plan:
                plan["risk"] = risk
                self.storage.update(plan)

            return {
                "status": "success",
                "agent": agent,
                "action": action,
                "summary": "Risque évalué par CriticEngine sur le vrai plan.",
                "plan_id": plan_id,
                "risk": risk,
            }

        return {
            "status": "skipped",
            "agent": agent,
            "action": action,
            "summary": "Action non implémentée dans TaskExecutor V1.",
        }

    def _execute_agent_creator_action(self, task: dict[str, Any]) -> dict[str, Any]:
        action = str(task.get("action") or "")
        plan = self._plan_for_task(task)
        step = self._step_for_task(task, plan)

        result = self.plan_executor._execute_step(step, plan)
        if result.get("status") == "skipped":
            return {
                "status": "skipped",
                "agent": task.get("agent"),
                "action": action,
                "summary": result.get("reason") or "Action agent_creator ignorée.",
                "result": result,
                "plan_id": task.get("plan_id"),
            }

        response: dict[str, Any] = {
            "status": "success",
            "agent": task.get("agent"),
            "action": action,
            "summary": self._agent_creator_summary(action, result),
            "result": result,
            "plan_id": task.get("plan_id"),
        }

        agent_path = result.get("path") or result.get("agent_path")
        if agent_path:
            response["agent_path"] = agent_path
            response["draft_only"] = result.get("draft_only", True)
            self._record_agent_draft(plan, str(agent_path), result)

        return response

    def _plan_for_task(self, task: dict[str, Any]) -> dict[str, Any]:
        plan_id = task.get("plan_id")
        plan = self.storage.get(str(plan_id)) if plan_id else None
        if plan:
            return plan

        return {
            "id": plan_id,
            "goal": task.get("goal"),
            "approved": True,
            "steps": [
                {
                    "title": task.get("title"),
                    "description": task.get("description"),
                    "agent": task.get("agent"),
                    "action": task.get("action"),
                }
            ],
        }

    def _step_for_task(self, task: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        title = task.get("title")
        for step in plan.get("steps", []):
            if step.get("action") == action and (
                not title or step.get("title") == title
            ):
                return dict(step)

        return {
            "title": task.get("title"),
            "description": task.get("description"),
            "agent": task.get("agent"),
            "action": action,
        }

    def _record_agent_draft(
        self,
        plan: dict[str, Any],
        agent_path: str,
        result: dict[str, Any],
    ) -> None:
        if not plan.get("id"):
            return

        plan["agent_path"] = agent_path
        plan["agent_draft"] = {
            "path": agent_path,
            "state": "draft_only",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "applied_to_core": result.get("applied_to_core", False),
        }
        self.storage.update(plan)

    def _agent_creator_summary(self, action: str, result: dict[str, Any]) -> str:
        if action == "analyze_agents":
            return f"Agents existants analysés ({result.get('files_found', 0)} fichier(s))."
        if action == "define_agent":
            return "Rôle du nouvel agent défini en mode brouillon."
        if action == "create_skeleton":
            return "Brouillon d'agent créé."
        if action == "check_integration":
            return "Intégration vérifiée sans modification du core."
        return "Action agent_creator traitée."


def get_task_executor() -> TaskExecutor:
    return TaskExecutor()
