from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from core.agent_factory.build_orchestrator import AgentBuildOrchestrator
from core.goals.execution_engine import GoalExecutionEngine
from core.projects.manager import ProjectManager
from core.runtime.sandbox.agent_sandbox import AgentSandbox
from core.validation.business_validator import BusinessValidator


class AllowGovernor:
    def authorize_agent_promotion(self, *, agent_name: str, requested_by: str) -> bool:
        return True

    def to_dict(self) -> dict:
        return {
            "runtime_mode": "normal",
            "autonomous_actions_allowed": True,
            "reason": None,
        }


def write_agent(path: Path, body: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def test_agent_ok_passes_sandbox(tmp_path: Path):
    workspace = tmp_path / "workspace"
    agent = write_agent(
        workspace / "agents" / "ok_agent.py",
        [
            "class Agent:",
            "    async def execute(self, text=''):",
            "        return {'status': 'ok', 'response': 'sandbox ok'}",
        ],
    )

    result = AgentSandbox(
        project_root=tmp_path,
        workspace=workspace,
        backend="python",
    ).execute_agent(agent, "test")

    assert result["ok"] is True
    assert result["result"]["response"] == "sandbox ok"
    assert result["sandbox"]["isolation"] == "python_audit"


def test_python_backend_skips_system_backends(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def unexpected_probe(_command):
        pytest.fail("python backend must not probe system executables")

    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.shutil.which",
        unexpected_probe,
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.pwd.getpwnam",
        lambda _user: pytest.fail("python backend must not probe system users"),
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.subprocess.run",
        lambda *_args, **_kwargs: pytest.fail(
            "python backend must not run backend probes"
        ),
    )

    diagnostics = AgentSandbox(
        project_root=tmp_path,
        backend="python",
    ).diagnostics()

    assert diagnostics["backend_used"] == "python"
    assert diagnostics["isolation_level"] == "process_python_audit"
    assert diagnostics["systemd_available"] is False
    assert diagnostics["user_available"] is False
    assert diagnostics["sudo_used"] is False
    assert diagnostics["sudo_available"] is False
    assert diagnostics["systemd_run_path"] is None


def test_python_backend_from_environment_never_uses_bwrap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = tmp_path / "workspace"
    agent = write_agent(
        workspace / "agents" / "mocked_agent.py",
        ["class Agent:", "    pass"],
    )
    monkeypatch.setenv("NERON_SANDBOX_BACKEND", "python")

    process = Mock()
    process.communicate.return_value = (
        '__NERON_AGENT_SANDBOX_RESULT__{"ok": true, "result": "mocked"}\n',
        "",
    )
    process.returncode = 0
    popen = Mock(return_value=process)
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.subprocess.Popen",
        popen,
    )

    sandbox = AgentSandbox(
        project_root=tmp_path,
        workspace=workspace,
    )
    result = sandbox.execute_agent(agent, "test")

    command = popen.call_args.args[0]
    assert command[0] != "bwrap"
    assert command[0] != "systemd-run"
    assert command[0] == sandbox.python_executable
    assert workspace.is_dir()
    assert (workspace / ".sandbox_tmp").is_dir()
    assert result["sandbox"]["backend_used"] == "python"
    assert result["sandbox"]["isolation"] == "python_audit"


def test_agent_timeout_fails_sandbox(tmp_path: Path):
    workspace = tmp_path / "workspace"
    agent = write_agent(
        workspace / "agents" / "timeout_agent.py",
        [
            "class Agent:",
            "    async def execute(self, text=''):",
            "        while True:",
            "            pass",
        ],
    )

    result = AgentSandbox(
        project_root=tmp_path,
        workspace=workspace,
        timeout=1,
        backend="python",
    ).execute_agent(agent, "test")

    assert result["ok"] is False
    assert result["sandbox"]["timed_out"] is True
    assert result["error"] == "agent_sandbox_timeout"


def test_agent_write_outside_workspace_is_blocked(tmp_path: Path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.txt"
    agent = write_agent(
        workspace / "agents" / "write_agent.py",
        [
            "from pathlib import Path",
            "class Agent:",
            "    async def execute(self, text=''):",
            f"        Path({str(outside)!r}).write_text('forbidden')",
            "        return {'status': 'ok', 'response': 'written'}",
        ],
    )

    result = AgentSandbox(
        project_root=tmp_path,
        workspace=workspace,
        backend="python",
    ).execute_agent(agent, "test")

    assert result["ok"] is False
    assert "sandbox_write_blocked" in result["error"]
    assert not outside.exists()


def test_auto_selects_systemd_when_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.shutil.which",
        lambda command: f"/usr/bin/{command}" if command == "systemd-run" else None,
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.pwd.getpwnam",
        lambda _user: Mock(),
    )

    sandbox = AgentSandbox(
        project_root=tmp_path,
        backend="auto",
        systemd_use_sudo="false",
    )

    assert sandbox.diagnostics()["backend_used"] == "systemd"
    assert sandbox.diagnostics()["fallback_reason"] is None


def test_auto_falls_back_when_systemd_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.shutil.which",
        lambda _command: None,
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.pwd.getpwnam",
        lambda _user: Mock(),
    )

    diagnostics = AgentSandbox(project_root=tmp_path, backend="auto").diagnostics()

    assert diagnostics["backend_used"] == "python"
    assert diagnostics["fallback_reason"] == "systemd_run_unavailable"


def test_auto_fallback_can_use_bubblewrap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.shutil.which",
        lambda command: "/usr/bin/bwrap" if command == "bwrap" else None,
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.pwd.getpwnam",
        lambda _user: Mock(),
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.subprocess.run",
        Mock(return_value=Mock(returncode=0, stdout="", stderr="")),
    )

    diagnostics = AgentSandbox(
        project_root=tmp_path,
        backend="auto",
        systemd_use_sudo="false",
    ).diagnostics()

    assert diagnostics["backend_used"] == "python"
    assert diagnostics["isolation_level"] == "kernel_bubblewrap"
    assert diagnostics["fallback_reason"] == "systemd_run_unavailable"


def test_auto_falls_back_when_system_user_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.shutil.which",
        lambda command: f"/usr/bin/{command}" if command == "systemd-run" else None,
    )

    def missing_user(_user):
        raise KeyError

    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.pwd.getpwnam",
        missing_user,
    )

    diagnostics = AgentSandbox(project_root=tmp_path, backend="auto").diagnostics()

    assert diagnostics["backend_used"] == "python"
    assert diagnostics["fallback_reason"] == "neron_agent_user_unavailable"


def test_systemd_command_contains_required_isolation_properties(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.shutil.which",
        lambda command: f"/usr/bin/{command}" if command == "systemd-run" else None,
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.pwd.getpwnam",
        lambda _user: Mock(),
    )
    sandbox = AgentSandbox(
        project_root=tmp_path,
        workspace=tmp_path / "workspace",
        backend="systemd",
        systemd_use_sudo="false",
    )

    command = sandbox._systemd_command(["python", "runner.py"], 30)

    assert command == [
        "/usr/bin/systemd-run",
        "--uid=neron-agent",
        "--property=DynamicUser=no",
        "--property=NoNewPrivileges=yes",
        "--property=PrivateTmp=yes",
        "--property=ProtectSystem=strict",
        "--property=ProtectHome=yes",
        f"--property=ReadWritePaths={tmp_path / 'workspace'}",
        f"--property=WorkingDirectory={tmp_path / 'workspace'}",
        "--property=MemoryMax=256M",
        "--property=CPUQuota=50%",
        "--property=RuntimeMaxSec=30",
        "--property=RestrictAddressFamilies=AF_UNIX",
        "--property=SystemCallFilter=@system-service",
        "--wait",
        "--pipe",
        "--",
        "python",
        "runner.py",
    ]


def test_systemd_execution_is_mocked_and_reports_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    agent = write_agent(
        tmp_path / "workspace" / "agents" / "mocked_agent.py",
        ["class Agent:", "    pass"],
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.shutil.which",
        lambda command: f"/usr/bin/{command}" if command == "systemd-run" else None,
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.pwd.getpwnam",
        lambda _user: Mock(),
    )
    process = Mock()
    process.communicate.return_value = (
        '__NERON_AGENT_SANDBOX_RESULT__{"ok": true, "result": "mocked"}\n',
        "",
    )
    process.returncode = 0
    popen = Mock(return_value=process)
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.subprocess.Popen",
        popen,
    )

    result = AgentSandbox(
        project_root=tmp_path,
        workspace=tmp_path / "workspace",
        backend="systemd",
        systemd_use_sudo="false",
    ).execute_agent(agent, "test")

    command = popen.call_args.args[0]
    assert command[0] == "/usr/bin/systemd-run"
    assert "--uid=neron-agent" in command
    assert "--property=RuntimeMaxSec=30" in command
    assert result["ok"] is True
    assert result["sandbox"]["backend_used"] == "systemd"
    assert result["sandbox"]["isolation_level"] == "kernel_systemd"


def test_systemd_auto_uses_sudo_for_non_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.shutil.which",
        lambda command: f"/usr/bin/{command}"
        if command in {"sudo", "systemd-run"}
        else None,
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.pwd.getpwnam",
        lambda _user: Mock(),
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.os.geteuid",
        lambda: 1000,
    )
    completed = Mock(returncode=0, stdout="systemd 257", stderr="")
    run = Mock(return_value=completed)
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.subprocess.run",
        run,
    )

    sandbox = AgentSandbox(
        project_root=tmp_path,
        backend="systemd",
        systemd_use_sudo="auto",
    )
    command = sandbox._systemd_command(["python", "runner.py"], 30)
    diagnostics = sandbox.diagnostics()

    run.assert_called_once_with(
        ["/usr/bin/sudo", "-n", "/usr/bin/systemd-run", "--version"],
        text=True,
        capture_output=True,
        timeout=3,
    )
    assert command[:3] == ["/usr/bin/sudo", "-n", "/usr/bin/systemd-run"]
    assert diagnostics["sudo_used"] is True
    assert diagnostics["sudo_available"] is True
    assert diagnostics["sudo_error"] is None
    assert diagnostics["systemd_run_path"] == "/usr/bin/systemd-run"


def test_systemd_strict_fails_cleanly_when_sudo_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    agent = write_agent(
        tmp_path / "workspace" / "agents" / "mocked_agent.py",
        ["class Agent:", "    pass"],
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.shutil.which",
        lambda command: "/usr/bin/systemd-run" if command == "systemd-run" else None,
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.pwd.getpwnam",
        lambda _user: Mock(),
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.os.geteuid",
        lambda: 1000,
    )
    popen = Mock()
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.subprocess.Popen",
        popen,
    )

    result = AgentSandbox(
        project_root=tmp_path,
        workspace=tmp_path / "workspace",
        backend="systemd",
        systemd_use_sudo="auto",
    ).execute_agent(agent, "test")

    assert result["ok"] is False
    assert result["error"] == "agent_sandbox_sudo_unavailable"
    assert result["sandbox"]["backend_error"] is True
    assert result["sandbox"]["sudo_used"] is True
    assert result["sandbox"]["sudo_available"] is False
    assert result["sandbox"]["sudo_error"] == "sudo_not_found"
    popen.assert_not_called()


def test_auto_falls_back_to_python_when_sudo_probe_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.shutil.which",
        lambda command: f"/usr/bin/{command}"
        if command in {"sudo", "systemd-run"}
        else None,
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.pwd.getpwnam",
        lambda _user: Mock(),
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.os.geteuid",
        lambda: 1000,
    )
    monkeypatch.setattr(
        "core.runtime.sandbox.agent_sandbox.subprocess.run",
        Mock(
            return_value=Mock(
                returncode=1,
                stdout="",
                stderr="sudo: a password is required",
            )
        ),
    )

    diagnostics = AgentSandbox(
        project_root=tmp_path,
        backend="auto",
        systemd_use_sudo="auto",
    ).diagnostics()

    assert diagnostics["backend_used"] == "python"
    assert diagnostics["fallback_reason"] == "systemd_sudo_unavailable"
    assert diagnostics["sudo_used"] is False
    assert diagnostics["sudo_available"] is False
    assert diagnostics["sudo_error"] == (
        "sudo_exit_1: sudo: a password is required"
    )


def test_business_validation_uses_agent_sandbox(tmp_path: Path):
    calls = []

    class RecordingSandbox:
        def execute_agent(self, agent_path, prompt, *, timeout, name):
            calls.append((Path(agent_path), prompt, timeout, name))
            return {
                "ok": True,
                "result": {"status": "ok", "response": "Réponse métier valide"},
                "sandbox": {"isolation": "test"},
            }

    agent = write_agent(
        tmp_path / "workspace" / "agents" / "business_agent.py",
        ["class Agent:", "    pass"],
    )
    validator = BusinessValidator(
        project_root=tmp_path,
        sandbox=RecordingSandbox(),
    )

    result = validator.validate(
        {"name": "business_agent", "goal": "Traiter une demande"},
        agent,
        "Créer un agent métier",
    )

    assert result["ok"] is True
    assert result["sandbox"]["isolation"] == "test"
    assert calls == [(agent.resolve(), "Créer un agent métier", 30, "business_validation")]


def test_goal_execution_engine_records_sandbox_events(tmp_path: Path):
    manager = ProjectManager(tmp_path / "data" / "projects.json")
    engine = GoalExecutionEngine(manager.sqlite_store)
    engine.enqueue_goal("goal-sandbox-pass", "Sandbox pass", "test")
    engine.start_goal("goal-sandbox-pass")

    engine.mark_sandbox_started("goal-sandbox-pass")
    engine.mark_sandbox_passed("goal-sandbox-pass")

    assert [
        event["status"]
        for event in engine.get_goal_events("goal-sandbox-pass")
        if event["step"] == "sandbox"
    ] == ["sandbox_started", "sandbox_passed"]


def test_goal_execution_engine_records_backend_events(tmp_path: Path):
    manager = ProjectManager(tmp_path / "data" / "projects.json")
    engine = GoalExecutionEngine(manager.sqlite_store)
    engine.enqueue_goal("goal-sandbox-backend", "Sandbox backend", "test")
    engine.start_goal("goal-sandbox-backend")

    for status in (
        "sandbox_backend_selected",
        "sandbox_systemd_started",
        "sandbox_systemd_failed",
        "sandbox_fallback_python",
    ):
        engine.mark_sandbox_backend_event(
            "goal-sandbox-backend",
            status,
            {"backend_used": "systemd"},
        )

    statuses = [
        event["status"]
        for event in engine.get_goal_events("goal-sandbox-backend")
    ]
    assert statuses[-4:] == [
        "sandbox_backend_selected",
        "sandbox_systemd_started",
        "sandbox_systemd_failed",
        "sandbox_fallback_python",
    ]


@pytest.mark.asyncio
async def test_registry_not_reached_when_sandbox_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    class FailingVerificationSandbox:
        def __init__(self):
            self.executions = 0

        def diagnostics(self):
            return {
                "backend_used": "python",
                "isolation_level": "process_python_audit",
                "systemd_available": False,
                "user_available": False,
                "fallback_reason": "systemd_run_unavailable",
            }

        def run_pytest(self, test_file, *, timeout, name):
            return {
                "name": name,
                "command": ["pytest", str(test_file)],
                "returncode": 0,
                "stdout_tail": "1 passed",
                "stderr_tail": "",
                "ran_at": "2026-06-10T00:00:00+00:00",
                "isolation": "test",
            }

        def execute_agent(self, agent_path, prompt, *, timeout=None, name):
            self.executions += 1
            if self.executions == 1:
                return {
                    "ok": True,
                    "result": {"status": "ok", "response": "Résultat métier"},
                    "sandbox": {"isolation": "test"},
                }
            return {
                "ok": False,
                "error": "sandbox_verification_rejected",
                "sandbox": {"isolation": "test"},
            }

    manager = ProjectManager(tmp_path / "data" / "projects.json")
    engine = GoalExecutionEngine(manager.sqlite_store)
    engine.enqueue_goal("goal-sandbox-failure", "Sandbox", "test")
    engine.start_goal("goal-sandbox-failure")
    sandbox = FailingVerificationSandbox()
    builder = AgentBuildOrchestrator(
        project_manager=manager,
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
        runtime_governor=AllowGovernor(),
        agent_sandbox=sandbox,
        execution_engine=engine,
    )
    monkeypatch.setattr(
        builder,
        "_register_agent",
        lambda *_args: pytest.fail("registry must not be reached"),
    )

    result = await builder.build_from_request(
        "Créer un agent nommé sandbox_failure_agent",
        tracking_context={"goal_id": "goal-sandbox-failure"},
    )

    project = result["project"]
    assert result["status"] == "failed"
    assert project["sandbox_status"] == "failed"
    assert project["sandbox_backend"] == "python"
    assert project["sandbox_isolation_level"] == "process_python_audit"
    assert project["registry_status"] == "not_registered"
    assert project["runtime_status"] == "not_available"
    statuses = [
        event["status"]
        for event in engine.get_goal_events("goal-sandbox-failure")
    ]
    assert "sandbox_backend_selected" in statuses
    assert "sandbox_fallback_python" in statuses
    assert "sandbox_started" in statuses
    assert "sandbox_failed" in statuses
