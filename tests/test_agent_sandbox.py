from __future__ import annotations

from pathlib import Path

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
    ).execute_agent(agent, "test")

    assert result["ok"] is True
    assert result["result"]["response"] == "sandbox ok"
    assert result["sandbox"]["isolation"] in {"bubblewrap", "python_audit"}


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
    ).execute_agent(agent, "test")

    assert result["ok"] is False
    assert "sandbox_write_blocked" in result["error"]
    assert not outside.exists()


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


@pytest.mark.asyncio
async def test_registry_not_reached_when_sandbox_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    class FailingVerificationSandbox:
        def __init__(self):
            self.executions = 0

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
    assert project["registry_status"] == "not_registered"
    assert project["runtime_status"] == "not_available"
    statuses = [
        event["status"]
        for event in engine.get_goal_events("goal-sandbox-failure")
    ]
    assert "sandbox_started" in statuses
    assert "sandbox_failed" in statuses
