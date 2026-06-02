from __future__ import annotations

from fastapi import APIRouter, Depends

from core.api.auth import verify_api_key
from core.evolution.supervisor import get_evolution_supervisor


router = APIRouter(prefix="/evolution", tags=["evolution"], dependencies=[Depends(verify_api_key)])


@router.get("/status")
async def evolution_status() -> dict:
    return get_evolution_supervisor().status()


@router.post("/propose")
async def propose_evolution() -> dict:
    supervisor = get_evolution_supervisor()
    proposals = supervisor.generate_proposals()
    submitted = await supervisor.submit_proposals(channel="api")
    return {"count": len(proposals), "proposals": proposals, "message": submitted["message"]}


@router.get("/proposals")
async def list_evolution_proposals() -> dict:
    proposals = get_evolution_supervisor().storage.latest_proposals()
    return {"count": len(proposals), "proposals": proposals}


@router.post("/accept/{proposal_id}")
async def accept_evolution(proposal_id: str) -> dict:
    return await get_evolution_supervisor().accept_proposal(
        proposal_id,
        source_channel="api",
        accepted_by="api",
    )


@router.post("/reject/{proposal_id}")
async def reject_evolution(proposal_id: str) -> dict:
    return get_evolution_supervisor().reject_proposal(
        proposal_id,
        source_channel="api",
        rejected_by="api",
    )


@router.post("/stop")
async def stop_evolution() -> dict:
    return await get_evolution_supervisor().stop()


@router.get("/runs")
async def list_evolution_runs(limit: int = 50) -> dict:
    runs = get_evolution_supervisor().storage.list_runs(limit=limit)
    return {"count": len(runs), "runs": runs}
