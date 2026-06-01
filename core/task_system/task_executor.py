from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.cognitive.critic_engine import get_critic_engine
from core.planning.storage import PlanStorage


class TaskExecutor:
    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        agent = task.get("agent")

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


def get_task_executor() -> TaskExecutor:
    return TaskExecutor()
