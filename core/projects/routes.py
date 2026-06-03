from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.api.auth import verify_api_key
from core.agent_factory.agent_creator import AgentCreator
from core.agent_factory.build_orchestrator import AgentBuildOrchestrator
from core.projects.manager import get_project_manager
from core.runtime.agents.agent_runtime_manager import get_agent_runtime_manager


router = APIRouter(tags=["projects"], dependencies=[Depends(verify_api_key)])


class AgentBuildRequest(BaseModel):
    query: str
    requested_by: str = "api"
    source_channel: str = "api"


@router.get("/projects")
async def list_projects(status: str | None = None, limit: int = 100) -> dict:
    manager = get_project_manager()
    projects = manager.list_projects(status=status, limit=limit)
    return {"count": len(projects), "projects": projects}


@router.get("/projects/search")
async def search_projects(q: str = Query(..., min_length=1), limit: int = 10) -> dict:
    manager = get_project_manager()
    projects = manager.find_project_by_query(q, limit=limit)
    return {"count": len(projects), "projects": projects}


@router.get("/projects/diagnostics/failures")
async def diagnose_project_failures(limit: int = 10) -> dict:
    manager = get_project_manager()
    return manager.diagnose_recent_failures(limit=limit)


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    manager = get_project_manager()
    project = manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@router.post("/agents/build")
async def build_agent(payload: AgentBuildRequest) -> dict:
    orchestrator = AgentBuildOrchestrator()
    return await orchestrator.build_from_request(
        payload.query,
        requested_by=payload.requested_by,
        source_channel=payload.source_channel,
    )


@router.post("/agents/proposals/{agent_request_id}/approve")
async def approve_agent_proposal(agent_request_id: str) -> dict:
    creator = AgentCreator()
    proposal = creator.get_proposal(agent_request_id)

    if not proposal:
        raise HTTPException(status_code=404, detail="Agent proposal not found")

    if proposal.get("status") != "pending_human_validation":
        raise HTTPException(
            status_code=409,
            detail=f"Agent proposal is not pending_human_validation: {proposal.get('status')}",
        )

    approved = creator.update_proposal(
        agent_request_id,
        {
            "status": "human_approved",
            "human_validation_required": False,
            "human_approved": True,
            "code_execution_allowed": True,
        },
    )
    if not approved:
        raise HTTPException(status_code=404, detail="Agent proposal not found")

    build_query = _build_query_from_proposal(approved)
    orchestrator = AgentBuildOrchestrator()
    build_result = await orchestrator.build_from_request(
        build_query,
        requested_by="agent_creator_approval",
        source_channel="api",
    )
    project = build_result.get("project") or {}
    created_files = list(project.get("created_files") or [])
    registered_agent = (
        project.get("registered_agent")
        or (project.get("result") or {}).get("agent")
        or (build_result.get("spec") or {}).get("name")
        or (build_result.get("agent") or {}).get("agent_name")
    )
    runtime_reload = get_agent_runtime_manager().reload()
    errors = _build_errors(build_result)

    final_proposal = creator.update_proposal(
        agent_request_id,
        {
            "build_status": build_result.get("status"),
            "build_project_id": project.get("project_id"),
            "created_files": created_files,
            "registered_agent": registered_agent,
            "runtime_reload": runtime_reload,
            "applied_to_core": build_result.get("status") == "completed" and bool(registered_agent),
            "errors": errors,
        },
    ) or approved

    return {
        "agent_request_id": agent_request_id,
        "proposal_status": final_proposal.get("status"),
        "build_status": build_result.get("status"),
        "created_files": created_files,
        "registered_agent": registered_agent,
        "runtime_reload": runtime_reload,
        "errors": errors,
        "project": project or None,
        "build": build_result,
    }


@router.get("/agents")
async def list_agents() -> dict:
    runtime = get_agent_runtime_manager()
    agents = runtime.list_agents()
    return {"count": len(agents), "agents": agents}


def _build_query_from_proposal(proposal: dict) -> str:
    agent_name = str(proposal.get("agent_name") or "").strip()
    goal = str(proposal.get("goal") or proposal.get("purpose") or "").strip()
    purpose = str(proposal.get("purpose") or "").strip()

    parts = []
    if agent_name:
        parts.append(f"Créer un agent nommé {agent_name}.")
    if goal:
        parts.append(goal)
    if purpose and purpose != goal:
        parts.append(purpose)
    return " ".join(parts).strip() or f"Créer un agent nommé {agent_name}"


def _build_errors(build_result: dict) -> list[str]:
    errors: list[str] = []
    if build_result.get("status") != "completed":
        project = build_result.get("project") or {}
        error = (
            build_result.get("error")
            or project.get("error")
            or build_result.get("response")
            or "agent_build_failed"
        )
        errors.append(str(error))
    return errors
