from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from modules.evolution.models import EvolutionProposal, EvolutionRun, utc_now_iso


EVOLUTION_STATE_PATH = Path("/etc/neron/data/evolution_state.json")


class EvolutionStorage:
    def __init__(self, path: Path = EVOLUTION_STATE_PATH) -> None:
        self.path = path
        self._lock = threading.RLock()

    def save_proposals(self, proposals: list[EvolutionProposal]) -> list[dict[str, Any]]:
        with self._lock:
            state = self._load()
            cycle_id = f"cycle_{uuid.uuid4().hex[:8]}"
            existing_ids = {str(item.get("proposal_id")) for item in state["proposals"]}
            saved: list[dict[str, Any]] = []
            for index, proposal in enumerate(proposals[:3], start=1):
                proposal.cycle_id = cycle_id
                proposal.index = index
                if not proposal.proposal_id or proposal.proposal_id in existing_ids:
                    proposal.proposal_id = f"evo_{uuid.uuid4().hex[:6]}"
                existing_ids.add(proposal.proposal_id)
                saved.append(proposal.to_dict())

            state["latest_cycle_id"] = cycle_id
            state["proposals"] = (state["proposals"] + saved)[-200:]
            self._save(state)
            return saved

    def latest_proposals(self) -> list[dict[str, Any]]:
        state = self._load()
        cycle_id = state.get("latest_cycle_id")
        if not cycle_id:
            return []
        proposals = [
            proposal
            for proposal in state.get("proposals", [])
            if proposal.get("cycle_id") == cycle_id
        ]
        return sorted(proposals, key=lambda item: int(item.get("index") or 0))

    def get_proposal(self, proposal_id_or_index: str) -> dict[str, Any] | None:
        wanted = str(proposal_id_or_index).strip()
        latest = self.latest_proposals()
        if wanted.isdigit():
            index = int(wanted)
            for proposal in latest:
                if int(proposal.get("index") or 0) == index:
                    return proposal

        for proposal in latest:
            proposal_id = str(proposal.get("proposal_id") or "")
            if proposal_id == wanted or proposal_id.startswith(wanted):
                return proposal
        return None

    def mark_proposal(self, proposal_id: str, status: str) -> None:
        with self._lock:
            state = self._load()
            for proposal in state["proposals"]:
                if proposal.get("proposal_id") == proposal_id:
                    proposal["status"] = status
                    proposal["updated_at"] = utc_now_iso()
            self._save(state)

    def record_decision(
        self,
        proposal: dict[str, Any],
        decision: str,
        *,
        source_channel: str,
        decided_by: str,
    ) -> dict[str, Any]:
        with self._lock:
            state = self._load()
            item = {
                "decision_id": f"decision_{uuid.uuid4().hex[:8]}",
                "proposal_id": proposal.get("proposal_id"),
                "proposal_index": proposal.get("index"),
                "decision": decision,
                "source_channel": source_channel,
                "decided_by": decided_by,
                "created_at": utc_now_iso(),
            }
            state["decisions"] = (state["decisions"] + [item])[-500:]
            self._save(state)
            return item

    def create_run(
        self,
        proposal: dict[str, Any],
        *,
        project_id: str | None,
        source_channel: str,
        accepted_by: str,
    ) -> dict[str, Any]:
        with self._lock:
            state = self._load()
            run = EvolutionRun(
                run_id=f"evo_run_{uuid.uuid4().hex[:8]}",
                proposal_id=str(proposal.get("proposal_id") or ""),
                project_id=project_id,
                status="pending",
                current_step="accepted",
                progress=5,
                source_channel=source_channel,
                accepted_by=accepted_by,
                proposal=proposal,
            ).to_dict()
            state["runs"] = (state["runs"] + [run])[-200:]
            self._save(state)
            return run

    def update_run(self, run_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            state = self._load()
            for run in state["runs"]:
                if run.get("run_id") != run_id:
                    continue
                run.update(updates)
                run["updated_at"] = utc_now_iso()
                self._save(state)
                return run
        return None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        for run in self._load().get("runs", []):
            if run.get("run_id") == run_id:
                return run
        return None

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        runs = self._load().get("runs", [])
        return list(reversed(runs[-max(1, min(limit, 200)) :]))

    def active_run(self) -> dict[str, Any] | None:
        for run in reversed(self._load().get("runs", [])):
            if run.get("status") in {"pending", "running"}:
                return run
        return None

    def set_stopped(self, stopped: bool) -> None:
        with self._lock:
            state = self._load()
            state["stopped"] = stopped
            self._save(state)

    def status(self) -> dict[str, Any]:
        state = self._load()
        return {
            "auto_evolution": True,
            "auto_approval": False,
            "stopped": bool(state.get("stopped")),
            "latest_cycle_id": state.get("latest_cycle_id"),
            "proposal_count": len(state.get("proposals", [])),
            "latest_proposals": self.latest_proposals(),
            "active_run": self.active_run(),
            "recent_runs": self.list_runs(limit=10),
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._default_state()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return self._default_state()
        if not isinstance(data, dict):
            return self._default_state()
        state = self._default_state()
        state.update({key: data.get(key, state[key]) for key in state})
        return state

    def _save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def _default_state() -> dict[str, Any]:
        return {
            "proposals": [],
            "decisions": [],
            "runs": [],
            "latest_cycle_id": None,
            "stopped": False,
        }
