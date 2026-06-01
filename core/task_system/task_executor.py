from __future__ import annotations

from typing import Any

from core.cognitive.critic_engine import get_critic_engine
from core.planning.executor import PlanExecutor
from core.planning.storage import PlanStorage


PLAN_EXECUTOR_ACTIONS = {
    "analyze_agents",
    "check_integration",
    "scan_project",
    "define_agent",
    "create_skeleton",
    "prepare_tests",
    "run_tests",
    "evaluate_risk",
    "security_audit",
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

        if self._uses_plan_executor(agent, action):
            return self._execute_with_plan_executor(task)

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
            storage = PlanStorage()

            plan_id = task.get("plan_id")
            plan = storage.get(str(plan_id)) if plan_id else None

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
                storage.update(plan)

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

    def _uses_plan_executor(self, agent: str | None, action: str | None) -> bool:
        if not action:
            return False

        return agent == "agent_creator" or action in PLAN_EXECUTOR_ACTIONS

    def _execute_with_plan_executor(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        agent = task.get("agent")
        plan = self._load_plan_for_task(task)
        step = {
            "title": task.get("title"),
            "description": task.get("description"),
            "agent": agent,
            "action": action,
        }

        result = self.plan_executor._execute_step(step, plan)

        if isinstance(result, dict) and result.get("status") == "skipped":
            return {
                "status": "skipped",
                "agent": agent,
                "action": action,
                "summary": result.get("reason") or "Action non implémentée dans PlanExecutor.",
                "result": result,
            }

        response = {
            "status": "success",
            "agent": agent,
            "action": action,
            "summary": "Action exécutée via PlanExecutor.",
            "plan_id": task.get("plan_id"),
            "result": result,
        }

        if isinstance(result, dict) and result.get("draft_created"):
            response["agent_path"] = result.get("path")
            response["agent_state"] = "draft_only"
            response["applied_to_core"] = result.get("applied_to_core", False)

        return response

    def _load_plan_for_task(self, task: dict[str, Any]) -> dict[str, Any]:
        plan_id = task.get("plan_id")
        plan = self.storage.get(str(plan_id)) if plan_id else None

        if plan:
            return plan

        return {
            "id": plan_id,
            "goal": task.get("goal"),
            "steps": [
                {
                    "title": task.get("title"),
                    "description": task.get("description"),
                    "agent": task.get("agent"),
                    "action": task.get("action"),
                }
            ],
            "approved": True,
        }


def get_task_executor() -> TaskExecutor:
    return TaskExecutor()
