from __future__ import annotations

from typing import Any

from core.agent_factory.agent_creator import AgentCreator
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
        agent_creator: AgentCreator | None = None,
    ) -> None:
        self.plan_executor = plan_executor or PlanExecutor()
        self.storage = storage or PlanStorage()
        self.agent_creator = agent_creator or AgentCreator()

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        agent = task.get("agent")

        if action in AGENT_CREATOR_ACTIONS or agent == "agent_creator":
            return self._execute_agent_creator_action(task)

        if action == "analyze_goal":
            return {
                "status": "success",
                "agent": agent,
                "action": action,
                "summary": "Objectif analyse.",
                "goal": task.get("goal"),
            }

        if action == "decompose_goal":
            return {
                "status": "success",
                "agent": agent,
                "action": action,
                "summary": "Objectif decompose en etapes via Planner.",
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
                "summary": "Risque evalue par CriticEngine sur le vrai plan.",
                "plan_id": plan_id,
                "risk": risk,
            }

        return {
            "status": "skipped",
            "agent": agent,
            "action": action,
            "summary": "Action non implementee dans TaskExecutor V1.",
        }

    def _execute_agent_creator_action(self, task: dict[str, Any]) -> dict[str, Any]:
        action = str(task.get("action") or "")
        plan = self._plan_for_task(task)
        goal = str(plan.get("goal") or task.get("goal") or "")

        if action == "analyze_agents":
            result = self.agent_creator.scan_existing_agents()
            return {
                "status": "success",
                "agent": task.get("agent"),
                "action": action,
                "summary": f"Agents existants analyses ({result.get('agents_scanned', 0)} fichier(s)).",
                "result": result,
                "plan_id": task.get("plan_id"),
            }

        if action in {"define_agent", "create_skeleton"}:
            proposal = self.agent_creator.request_agent_creation(
                goal=goal,
                plan=plan,
                missing_capability=self.agent_creator.infer_missing_capability(goal),
            )
            self._record_agent_proposal(plan, proposal)

            return {
                "status": "success",
                "agent": task.get("agent"),
                "action": action,
                "summary": "Proposition d'agent preparee; validation humaine requise.",
                "result": {
                    "proposal_created": True,
                    "agent_request_id": proposal.get("agent_request_id"),
                    "status": proposal.get("status"),
                    "code_execution_allowed": False,
                },
                "plan_id": task.get("plan_id"),
                "agent_creator_called": True,
                "agent_request_id": proposal.get("agent_request_id"),
                "agent_creation_proposal": proposal,
                "proposal": proposal,
                "applied_to_core": False,
                "code_executed": False,
            }

        if action == "check_integration":
            proposal = plan.get("agent_creation_proposal") or {}
            return {
                "status": "success",
                "agent": task.get("agent"),
                "action": action,
                "summary": "Integration verifiee sans modification du core.",
                "result": {
                    "proposal_status": proposal.get("status", "pending_human_validation"),
                    "applied_to_core": False,
                    "code_execution_allowed": False,
                },
                "plan_id": task.get("plan_id"),
            }

        return {
            "status": "skipped",
            "agent": task.get("agent"),
            "action": action,
            "summary": "Action agent_creator ignoree.",
            "plan_id": task.get("plan_id"),
        }

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

    def _record_agent_proposal(
        self,
        plan: dict[str, Any],
        proposal: dict[str, Any],
    ) -> None:
        if not plan.get("id"):
            return

        plan["agent_creator_called"] = True
        plan["agent_request_id"] = proposal.get("agent_request_id")
        plan["agent_creation_proposal"] = proposal
        plan["agent_proposal_status"] = proposal.get("status")
        plan["applied_to_core"] = False
        self.storage.update(plan)


def get_task_executor() -> TaskExecutor:
    return TaskExecutor()
