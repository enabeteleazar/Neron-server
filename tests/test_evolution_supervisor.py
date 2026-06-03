from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Awaitable, Callable

import pytest

from core.agents.communication.telegram_agent import route_evolution_telegram_text
from core.evolution import codex_runner as codex_runner_module
from core.evolution.codex_runner import (
    CODEX_MISSING_ERROR,
    CodexRunner,
    build_codex_exec_command,
    redact_secrets,
    resolve_codex_bin,
)
from core.evolution.models import CommandResult
from core.evolution.proposal_engine import ProposalEngine
from core.evolution.storage import EvolutionStorage
from core.evolution.supervisor import EvolutionSupervisor
from core.projects.manager import ProjectManager


class FakeCodexRunner:
    def __init__(self, *, tests_ok: bool = True, codex_delay: float = 0.0) -> None:
        self.tests_ok = tests_ok
        self.codex_delay = codex_delay
        self.codex_calls = 0
        self.tests_calls = 0
        self.commit_calls = 0
        self.cancel_calls = 0
        self.codex_started = asyncio.Event()
        self.codex_continue = asyncio.Event()
        self.codex_continue.set()

    async def run_codex(self, prompt: str, run_id: str) -> CommandResult:
        self.codex_calls += 1
        self.codex_started.set()
        await self.codex_continue.wait()
        if self.codex_delay:
            await asyncio.sleep(self.codex_delay)
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


class FailingCodexRunner(FakeCodexRunner):
    async def run_codex(self, prompt: str, run_id: str) -> CommandResult:
        self.codex_calls += 1
        self.codex_started.set()
        return CommandResult(
            "codex",
            ["codex", "exec", prompt],
            2,
            stderr="error: unexpected argument '--ask-for-approval' found",
        )


def make_supervisor(
    tmp_path: Path,
    runner: FakeCodexRunner | None = None,
    *,
    timeout_seconds: int | None = None,
    telegram_notifier: Callable[[str], Awaitable[None]] | None = None,
) -> EvolutionSupervisor:
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
        timeout_seconds=timeout_seconds,
        telegram_notifier=telegram_notifier,
    )


def make_executable(path: Path, content: str = "#!/bin/sh\nexit 0\n") -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)
    return path


async def wait_for_run_status(
    supervisor: EvolutionSupervisor,
    run_id: str,
    status: str,
    *,
    timeout: float = 2.0,
) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = supervisor.storage.get_run(run_id)
        if run and run.get("status") == status:
            return run
        await asyncio.sleep(0.01)
    raise AssertionError(f"run {run_id} did not reach {status}")


def test_generates_three_proposals_max(tmp_path: Path):
    supervisor = make_supervisor(tmp_path)
    proposals = supervisor.generate_proposals()

    assert 1 <= len(proposals) <= 3


def test_proposal_contains_non_empty_codex_prompt(tmp_path: Path):
    supervisor = make_supervisor(tmp_path)
    proposals = supervisor.generate_proposals()

    assert all(proposal["codex_prompt"].strip() for proposal in proposals)


def test_todo_scanner_ignores_python_symbols_and_runtime_strings(tmp_path: Path):
    workspace = tmp_path / "repo"
    source_dir = workspace / "core"
    docs_dir = workspace / "docs"
    source_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)
    (source_dir / "constants.py").write_text(
        '\n'.join(
            [
                'TODO_KEYWORDS = ["todo"]',
                'summary = "TODO/FIXME détecté(s) dans le code suivi."',
                'text = "FIXME inside runtime string only"',
            ]
        ),
        encoding="utf-8",
    )
    (docs_dir / "scanner.md").write_text(
        "Le moteur documente les marqueurs TODO/FIXME sans créer une dette.",
        encoding="utf-8",
    )

    observation = ProposalEngine(workspace).observe()

    assert observation["todos"] == []


def test_todo_scanner_keeps_python_comments_and_docstrings(tmp_path: Path):
    workspace = tmp_path / "repo"
    source_dir = workspace / "core"
    source_dir.mkdir(parents=True)
    (source_dir / "module.py").write_text(
        '\n'.join(
            [
                '"""',
                "TODO: clarify public contract",
                '"""',
                "",
                "# FIXME: handle malformed payloads",
                "VALUE = 'not a marker'",
            ]
        ),
        encoding="utf-8",
    )

    observation = ProposalEngine(workspace).observe()

    markers = {(item["line"], item["text"]) for item in observation["todos"]}
    assert (2, "TODO: clarify public contract") in markers
    assert (5, "# FIXME: handle malformed payloads") in markers


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


def test_accept_evolution_returns_immediately_and_runs_in_background(tmp_path: Path):
    async def scenario():
        runner = FakeCodexRunner(tests_ok=True)
        runner.codex_continue.clear()
        supervisor = make_supervisor(tmp_path, runner)
        supervisor.generate_proposals()

        started_at = time.monotonic()
        result = await supervisor.accept_proposal("1")
        elapsed = time.monotonic() - started_at

        assert elapsed < 0.1
        assert result["status"] == "accepted"
        assert result["message"] == "Évolution acceptée. Exécution en arrière-plan."
        assert result["run"]["status"] == "running"

        await asyncio.wait_for(runner.codex_started.wait(), timeout=1)
        runner.codex_continue.set()
        run = await wait_for_run_status(supervisor, result["run"]["run_id"], "completed")
        assert run["commit_hash"] == "abc123"

    asyncio.run(scenario())


def test_background_run_passes_to_running_and_worker_executes(tmp_path: Path):
    async def scenario():
        runner = FakeCodexRunner(tests_ok=True)
        runner.codex_continue.clear()
        supervisor = make_supervisor(tmp_path, runner)
        supervisor.generate_proposals()

        result = await supervisor.accept_proposal("1")
        status = supervisor.status()

        assert status["active_run"]["run_id"] == result["run"]["run_id"]
        assert status["active_run"]["status"] == "running"
        assert status["active_run"]["current_step"] in {"accepted", "codex_running"}
        assert status["active_run"]["progress"] >= 10

        await asyncio.wait_for(runner.codex_started.wait(), timeout=1)
        running = supervisor.storage.get_run(result["run"]["run_id"])
        assert running["status"] == "running"
        assert running["current_step"] == "codex_running"
        assert runner.codex_calls == 1

        runner.codex_continue.set()
        await wait_for_run_status(supervisor, result["run"]["run_id"], "completed")

    asyncio.run(scenario())


def test_codex_runner_is_mocked_and_success_commits_and_pushes(tmp_path: Path):
    runner = FakeCodexRunner(tests_ok=True)
    supervisor = make_supervisor(tmp_path, runner)
    supervisor.generate_proposals()

    accepted = asyncio.run(supervisor.accept_proposal("1", execute=False))
    result = asyncio.run(supervisor.run_accepted_proposal(accepted["run"]["run_id"]))

    assert result["status"] == "completed"
    assert runner.codex_calls == 1
    assert runner.tests_calls == 1
    assert runner.commit_calls == 1
    assert result["commit_hash"] == "abc123"


def test_failed_tests_prevent_commit_and_push(tmp_path: Path):
    runner = FakeCodexRunner(tests_ok=False)
    supervisor = make_supervisor(tmp_path, runner)
    supervisor.generate_proposals()

    accepted = asyncio.run(supervisor.accept_proposal("1", execute=False))
    result = asyncio.run(supervisor.run_accepted_proposal(accepted["run"]["run_id"]))

    assert result["status"] == "failed"
    assert runner.codex_calls == 1
    assert runner.tests_calls == 1
    assert runner.commit_calls == 0
    assert "Tests en échec" in result["error"]


def test_codex_failure_context_is_stored_on_project(tmp_path: Path):
    runner = FailingCodexRunner()
    supervisor = make_supervisor(tmp_path, runner)
    supervisor.generate_proposals()

    accepted = asyncio.run(supervisor.accept_proposal("1", execute=False))
    result = asyncio.run(supervisor.run_accepted_proposal(accepted["run"]["run_id"]))
    project = supervisor.project_manager.get_project(result["project_id"])
    diagnostics = supervisor.project_manager.diagnose_recent_failures(limit=1)

    assert result["status"] == "failed"
    assert project is not None
    context = project["metadata"]["failure_context"]
    assert context["retry_requires_validation"] is True
    assert context["codex"]["returncode"] == 2
    assert "unexpected argument" in context["codex"]["stderr_tail"]
    assert diagnostics["projects"][0]["category"] == "codex_cli_arguments"
    assert runner.tests_calls == 0
    assert runner.commit_calls == 0


def test_after_completion_new_proposals_are_generated_but_not_executed(tmp_path: Path):
    runner = FakeCodexRunner(tests_ok=True)
    supervisor = make_supervisor(tmp_path, runner)
    first = supervisor.generate_proposals()

    accepted = asyncio.run(supervisor.accept_proposal("1", execute=False))
    result = asyncio.run(supervisor.run_accepted_proposal(accepted["run"]["run_id"]))
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


def test_second_acceptance_is_refused_during_background_run(tmp_path: Path):
    async def scenario():
        runner = FakeCodexRunner(tests_ok=True)
        runner.codex_continue.clear()
        supervisor = make_supervisor(tmp_path, runner)
        supervisor.generate_proposals()

        first = await supervisor.accept_proposal("1")
        await asyncio.wait_for(runner.codex_started.wait(), timeout=1)
        second = await supervisor.accept_proposal("2")

        assert first["status"] == "accepted"
        assert second["status"] == "refused"
        assert second["reason"] == "evolution_run_already_active"
        assert second["active_run"]["run_id"] == first["run"]["run_id"]

        runner.codex_continue.set()
        await wait_for_run_status(supervisor, first["run"]["run_id"], "completed")

    asyncio.run(scenario())


def test_status_stays_accessible_during_background_run(tmp_path: Path):
    async def scenario():
        runner = FakeCodexRunner(tests_ok=True)
        runner.codex_continue.clear()
        supervisor = make_supervisor(tmp_path, runner)
        supervisor.generate_proposals()

        result = await supervisor.accept_proposal("1")
        await asyncio.wait_for(runner.codex_started.wait(), timeout=1)
        status = supervisor.status()

        assert status["active_run"]["run_id"] == result["run"]["run_id"]
        assert status["active_run"]["status"] == "running"
        assert status["active_run"]["current_step"] == "codex_running"
        assert status["active_run"]["progress"] == 25

        runner.codex_continue.set()
        await wait_for_run_status(supervisor, result["run"]["run_id"], "completed")

    asyncio.run(scenario())


def test_background_run_sends_final_notification(tmp_path: Path):
    async def scenario():
        notifications: list[str] = []

        async def notify(message: str) -> None:
            notifications.append(message)

        runner = FakeCodexRunner(tests_ok=True)
        supervisor = make_supervisor(tmp_path, runner, telegram_notifier=notify)
        supervisor.generate_proposals()

        result = await supervisor.accept_proposal("1")
        await wait_for_run_status(supervisor, result["run"]["run_id"], "completed")

        assert any("Évolution completed" in notification for notification in notifications)
        assert any("Commit : abc123" in notification for notification in notifications)

    asyncio.run(scenario())


def test_background_run_uses_configurable_timeout(tmp_path: Path):
    async def scenario():
        runner = FakeCodexRunner(tests_ok=True)
        runner.codex_continue.clear()
        supervisor = make_supervisor(tmp_path, runner, timeout_seconds=1)
        supervisor.generate_proposals()
        supervisor.timeout_seconds = 0.01

        result = await supervisor.accept_proposal("1")
        run = await wait_for_run_status(supervisor, result["run"]["run_id"], "failed")

        assert "timeout" in run["error"].lower()
        assert runner.cancel_calls == 1

    asyncio.run(scenario())


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
    assert response == "Évolution acceptée. Exécution en arrière-plan."


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


def test_codex_bin_resolves_from_neron_codex_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    codex = make_executable(tmp_path / "codex-custom")
    monkeypatch.setenv("NERON_CODEX_BIN", str(codex))
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(codex_runner_module, "KNOWN_CODEX_PATHS", ())

    codex_bin, error = resolve_codex_bin()

    assert codex_bin == str(codex)
    assert error is None


def test_codex_bin_resolves_from_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = make_executable(bin_dir / "codex")
    monkeypatch.delenv("NERON_CODEX_BIN", raising=False)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(codex_runner_module, "KNOWN_CODEX_PATHS", ())

    codex_bin, error = resolve_codex_bin()

    assert codex_bin == str(codex)
    assert error is None


def test_codex_bin_resolves_from_known_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    codex = make_executable(tmp_path / "known-codex")
    monkeypatch.delenv("NERON_CODEX_BIN", raising=False)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(codex_runner_module, "KNOWN_CODEX_PATHS", (codex,))

    codex_bin, error = resolve_codex_bin()

    assert codex_bin == str(codex)
    assert error is None


def test_codex_exec_command_uses_old_supported_syntax():
    command = build_codex_exec_command(
        "/usr/bin/codex",
        "Options:\n  --ask-for-approval <POLICY>\n  --sandbox <SANDBOX_MODE>\n",
        "mission",
    )

    assert command == [
        "/usr/bin/codex",
        "exec",
        "--ask-for-approval",
        "never",
        "--sandbox",
        "workspace-write",
        "mission",
    ]


def test_codex_exec_command_uses_new_supported_syntax():
    command = build_codex_exec_command(
        "/usr/bin/codex",
        "Options:\n  --approval-mode <MODE>\n  --sandbox-mode <SANDBOX_MODE>\n",
        "mission",
    )

    assert command == [
        "/usr/bin/codex",
        "exec",
        "--approval-mode",
        "never",
        "--sandbox-mode",
        "workspace-write",
        "mission",
    ]


def test_codex_exec_command_omits_unsupported_options():
    command = build_codex_exec_command("/usr/bin/codex", "Options:\n  --json\n", "mission")

    assert command == ["/usr/bin/codex", "exec", "mission"]


def test_codex_bin_returns_clear_error_when_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NERON_CODEX_BIN", raising=False)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(codex_runner_module, "KNOWN_CODEX_PATHS", ())

    codex_bin, error = resolve_codex_bin()

    assert codex_bin is None
    assert error == CODEX_MISSING_ERROR


def test_codex_runner_does_not_launch_subprocess_when_codex_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    calls = 0

    async def fake_create_subprocess_exec(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("subprocess should not be launched")

    monkeypatch.delenv("NERON_CODEX_BIN", raising=False)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(codex_runner_module, "KNOWN_CODEX_PATHS", ())
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    runner = CodexRunner(workspace=tmp_path)

    result = asyncio.run(runner.run_codex("do the work", "run-1"))

    assert calls == 0
    assert not result.ok
    assert result.stderr == CODEX_MISSING_ERROR


def test_codex_runner_runs_exec_help_preflight_before_real_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    codex = make_executable(tmp_path / "codex")
    calls: list[tuple[str, list[str]]] = []

    async def fake_run_command(name: str, command: list[str], *, timeout: int | None = None):
        calls.append((name, command))
        if name == "codex_exec_help":
            return CommandResult(name, command, 0, stdout="Options:\n  --sandbox <SANDBOX_MODE>\n")
        return CommandResult(name, command, 0, stdout="done")

    monkeypatch.setenv("NERON_CODEX_BIN", str(codex))
    runner = CodexRunner(workspace=tmp_path)
    monkeypatch.setattr(runner, "run_command", fake_run_command)

    result = asyncio.run(runner.run_codex("mission", "run-1"))

    assert result.ok
    assert calls[0] == ("codex_exec_help", [str(codex), "exec", "--help"])
    assert calls[1] == ("codex", [str(codex), "exec", "--sandbox", "workspace-write", "mission"])


def test_evolution_status_exposes_codex_diagnostics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    codex = make_executable(
        tmp_path / "codex",
        """#!/bin/sh
if [ "$1" = "--version" ]; then
  echo "codex-cli 1.2.3"
  exit 0
fi
if [ "$1" = "exec" ] && [ "$2" = "--help" ]; then
  echo "Options:"
  echo "  --approval-mode <MODE>"
  echo "  --sandbox-mode <SANDBOX_MODE>"
  exit 0
fi
exit 0
""",
    )
    monkeypatch.setenv("NERON_CODEX_BIN", str(codex))
    supervisor = EvolutionSupervisor(
        storage=EvolutionStorage(tmp_path / "evolution_state.json"),
        proposal_engine=ProposalEngine(tmp_path),
        codex_runner=CodexRunner(workspace=tmp_path),
        project_manager=ProjectManager(tmp_path / "projects.json"),
        workspace=tmp_path,
    )

    status = supervisor.status()

    assert status["codex_available"] is True
    assert status["codex_bin"] == str(codex)
    assert status["codex_error"] is None
    assert status["codex_version"] == "codex-cli 1.2.3"
    assert status["codex_exec_supported_options"] == ["--approval-mode", "--sandbox-mode"]
