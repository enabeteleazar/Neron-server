from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from core.agents.communication.telegram_agent import route_evolution_telegram_text
from core.evolution.codex_runner import redact_secrets
from core.evolution.models import CommandResult
from core.evolution.proposal_engine import ProposalEngine
from core.evolution.storage import EvolutionStorage
from core.evolution.supervisor import EvolutionSupervisor
from core.projects.manager import ProjectManager


class FakeCodexRunner:
    def __init__(self, *, tests_ok: bool = True) -> None:
        self.tests_ok = tests_ok
        self.codex_calls = 0
        self.tests_calls = 0
        self.commit_calls = 0
        self.cancel_calls = 0

    async def run_codex(self, prompt: str, run_id: str) -> CommandResult:
        self.codex_calls += 1
        return CommandResult("codex", ["codex"], 0, stdout=f"run {run_id}: {prompt[:20]}")

    async def run_tests(self) -> list[CommandResult]:
        self.tests_calls += 1
        if self.tests_ok:
            return [
                CommandResult("compileall", ["python", "-m", "compileall", "core"], 0),
                CommandResult("parallel", ["pytest", "tests/test_parallel.py", "-v"], 0),
                CommandResult("git_diff_check", ["git", "diff", "--check"], 0),
            ]
        return [CommandResult("compileall", ["python", "-m", "compileall", "core"], 1, stderr="boom")]

    async def commit_and_push(self, message: str) -> dict:
        self.commit_calls += 1
        return {
            "ok": True,
            "pushed": True,
            "commit_hash": "abc123",
            "branch": "develop",
            "message": message,
        }

    async def cancel(self) -> None:
        self.cancel_calls += 1


def make_supervisor(tmp_path: Path, runner: FakeCodexRunner | None = None) -> EvolutionSupervisor:
    workspace = tmp_path / "repo"
    (workspace / "core").mkdir(parents=True)
    (workspace / "core" / "app.py").write_text("", encoding="utf-8")
    (workspace / "tests").mkdir()
    (workspace / "docs" / "architecture").mkdir(parents=True)
    storage = EvolutionStorage(tmp_path / "evolution_state.json")
    project_manager = ProjectManager(tmp_path / "projects.json")
    return EvolutionSupervisor(
        storage=storage,
        proposal_engine=ProposalEngine(workspace),
        codex_runner=runner or FakeCodexRunner(),
        project_manager=project_manager,
        workspace=workspace,
    )


def test_generates_three_proposals_max(tmp_path: Path):
    supervisor = make_supervisor(tmp_path)
    proposals = supervisor.generate_proposals()

    assert 1 <= len(proposals) <= 3


def test_proposal_contains_non_empty_codex_prompt(tmp_path: Path):
    supervisor = make_supervisor(tmp_path)
    proposals = supervisor.generate_proposals()

    assert all(proposal["codex_prompt"].strip() for proposal in proposals)


def test_no_proposal_is_executed_without_acceptance(tmp_path: Path):
    runner = FakeCodexRunner()
    supervisor = make_supervisor(tmp_path, runner)

    supervisor.generate_proposals()

    assert runner.codex_calls == 0
    assert supervisor.storage.list_runs() == []


def test_acceptance_creates_evolution_run_and_project(tmp_path: Path):
    runner = FakeCodexRunner(tests_ok=True)
    supervisor = make_supervisor(tmp_path, runner)
    supervisor.generate_proposals()

    result = asyncio.run(supervisor.accept_proposal("1", execute=False))

    assert result["status"] == "accepted"
    assert result["run"]["status"] == "running"
    assert result["project"]["type"] == "evolution"
    assert result["project"]["metadata"]["proposal_id"]
    assert runner.codex_calls == 0


def test_codex_runner_is_mocked_and_success_commits_and_pushes(tmp_path: Path):
    runner = FakeCodexRunner(tests_ok=True)
    supervisor = make_supervisor(tmp_path, runner)
    supervisor.generate_proposals()

    result = asyncio.run(supervisor.accept_proposal("1"))

    assert result["status"] == "completed"
    assert runner.codex_calls == 1
    assert runner.tests_calls == 1
    assert runner.commit_calls == 1
    assert result["run"]["commit_hash"] == "abc123"


def test_failed_tests_prevent_commit_and_push(tmp_path: Path):
    runner = FakeCodexRunner(tests_ok=False)
    supervisor = make_supervisor(tmp_path, runner)
    supervisor.generate_proposals()

    result = asyncio.run(supervisor.accept_proposal("1"))

    assert result["status"] == "failed"
    assert runner.codex_calls == 1
    assert runner.tests_calls == 1
    assert runner.commit_calls == 0
    assert "Tests en échec" in result["run"]["error"]


def test_after_completion_new_proposals_are_generated_but_not_executed(tmp_path: Path):
    runner = FakeCodexRunner(tests_ok=True)
    supervisor = make_supervisor(tmp_path, runner)
    first = supervisor.generate_proposals()

    result = asyncio.run(supervisor.accept_proposal("1"))
    latest = supervisor.storage.latest_proposals()

    assert result["status"] == "completed"
    assert latest
    assert latest[0]["cycle_id"] != first[0]["cycle_id"]
    assert runner.codex_calls == 1


def test_second_mission_is_refused_when_one_is_running(tmp_path: Path):
    runner = FakeCodexRunner(tests_ok=True)
    supervisor = make_supervisor(tmp_path, runner)
    supervisor.generate_proposals()
    asyncio.run(supervisor.accept_proposal("1", execute=False))

    result = asyncio.run(supervisor.accept_proposal("2", execute=False))

    assert result["status"] == "refused"
    assert result["reason"] == "evolution_run_already_active"
    assert runner.codex_calls == 0


def test_telegram_accept_command_is_routable(tmp_path: Path):
    runner = FakeCodexRunner(tests_ok=True)
    supervisor = make_supervisor(tmp_path, runner)
    supervisor.generate_proposals()

    response = asyncio.run(
        route_evolution_telegram_text(
            "/accept_evolution 1",
            supervisor=supervisor,
            user_id="test-chat",
        )
    )

    assert response is not None
    assert "Évolution completed" in response
    assert runner.codex_calls == 1


def test_telegram_natural_language_lists_three_proposals_max(tmp_path: Path):
    supervisor = make_supervisor(tmp_path)

    response = asyncio.run(
        route_evolution_telegram_text(
            "Quelles sont les prochaines évolutions ?",
            supervisor=supervisor,
            user_id="test-chat",
        )
    )

    assert response is not None
    assert "Évolutions proposées" in response
    assert response.count("/accept_evolution") <= 4


def test_storage_persists_proposals_and_runs(tmp_path: Path):
    supervisor = make_supervisor(tmp_path)
    proposals = supervisor.generate_proposals()
    asyncio.run(supervisor.accept_proposal("1", execute=False))

    reloaded = EvolutionStorage(tmp_path / "evolution_state.json")

    assert reloaded.latest_proposals()[0]["proposal_id"] == proposals[0]["proposal_id"]
    assert reloaded.list_runs()[0]["proposal_id"] == proposals[0]["proposal_id"]


def test_logs_are_filtered_to_avoid_secrets():
    redacted = redact_secrets(
        "TOKEN=abc123 password:supersecret Authorization: Bearer eyJ.test X-API-Key: key123"
    )

    assert "abc123" not in redacted
    assert "supersecret" not in redacted
    assert "eyJ.test" not in redacted
    assert "key123" not in redacted
