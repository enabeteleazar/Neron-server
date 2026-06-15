from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvolutionProposal:
    proposal_id: str
    title: str
    priority: str
    type: str
    summary: str
    expected_gain: str
    risk: str
    areas: list[str]
    acceptance_criteria: list[str]
    codex_prompt: str
    estimate: str
    cycle_id: str = ""
    index: int = 0
    status: str = "proposed"
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvolutionProposal":
        return cls(
            proposal_id=str(data.get("proposal_id") or ""),
            title=str(data.get("title") or ""),
            priority=str(data.get("priority") or "future"),
            type=str(data.get("type") or "feature"),
            summary=str(data.get("summary") or ""),
            expected_gain=str(data.get("expected_gain") or ""),
            risk=str(data.get("risk") or "low"),
            areas=list(data.get("areas") or []),
            acceptance_criteria=list(data.get("acceptance_criteria") or []),
            codex_prompt=str(data.get("codex_prompt") or ""),
            estimate=str(data.get("estimate") or "medium"),
            cycle_id=str(data.get("cycle_id") or ""),
            index=int(data.get("index") or 0),
            status=str(data.get("status") or "proposed"),
            created_at=str(data.get("created_at") or utc_now_iso()),
        )


@dataclass
class CommandResult:
    name: str
    command: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"ok": self.ok}


@dataclass
class EvolutionRun:
    run_id: str
    proposal_id: str
    project_id: str | None
    status: str
    current_step: str
    progress: int
    source_channel: str
    accepted_by: str
    proposal: dict[str, Any]
    tests: list[dict[str, Any]] = field(default_factory=list)
    codex: dict[str, Any] | None = None
    commit: dict[str, Any] | None = None
    commit_hash: str | None = None
    branch: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvolutionRun":
        return cls(
            run_id=str(data.get("run_id") or ""),
            proposal_id=str(data.get("proposal_id") or ""),
            project_id=data.get("project_id"),
            status=str(data.get("status") or "pending"),
            current_step=str(data.get("current_step") or "accepted"),
            progress=int(data.get("progress") or 0),
            source_channel=str(data.get("source_channel") or "api"),
            accepted_by=str(data.get("accepted_by") or "user"),
            proposal=dict(data.get("proposal") or {}),
            tests=list(data.get("tests") or []),
            codex=data.get("codex"),
            commit=data.get("commit"),
            commit_hash=data.get("commit_hash"),
            branch=data.get("branch"),
            error=data.get("error"),
            created_at=str(data.get("created_at") or utc_now_iso()),
            updated_at=str(data.get("updated_at") or utc_now_iso()),
        )
