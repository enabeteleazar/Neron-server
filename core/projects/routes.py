from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.agent_factory.build_orchestrator import AgentBuildOrchestrator
from core.projects.manager import get_project_manager
from core.runtime.agents.agent_runtime_manager import get_agent_runtime_manager


router = APIRouter(tags=["projects"])


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


@router.get("/agents")
async def list_agents() -> dict:
    runtime = get_agent_runtime_manager()
    agents = runtime.list_agents()
    return {"count": len(agents), "agents": agents}
