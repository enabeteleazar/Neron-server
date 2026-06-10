from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from core.agent_factory import build_orchestrator as build_module
from core.agent_factory.build_orchestrator import AgentBuildOrchestrator
from core.agent_factory.promoter import promote_agent
from core.goals import goal_manager, persistence, routes
from core.goals.goal_orchestrator import GoalOrchestrator
from core.planning.storage import PlanStorage
from core.pipeline.routing import agent_router
from core.projects.manager import ProjectManager
from core.runtime.governor import RuntimeGovernor


class FakeGovernor:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed

    def authorize_agent_promotion(self, *, agent_name: str, requested_by: str) -> bool:
        return self.allowed

    def to_dict(self) -> dict:
        return {
            "runtime_mode": "normal" if self.allowed else "survival",
            "autonomous_actions_allowed": self.allowed,
            "reason": None if self.allowed else "runtime_pressure",
        }


def make_builder(
    tmp_path: Path,
    *,
    governor: FakeGovernor | None = None,
) -> AgentBuildOrchestrator:
    return AgentBuildOrchestrator(
        project_manager=ProjectManager(tmp_path / "data" / "projects.json"),
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
        runtime_governor=governor or FakeGovernor(True),
    )


@pytest.mark.asyncio
async def test_governor_refusal_blocks_promotion_after_tests(tmp_path: Path):
    builder = make_builder(tmp_path, governor=FakeGovernor(False))

    result = await builder.build_from_request("Créer un agent nommé refused_agent")

    project = result["project"]
    assert result["status"] == "failed"
    assert project["validation_status"] == "passed"
    assert project["compile_status"] == "passed"
    assert project["test_status"] == "passed"
    assert project["governor_status"] == "refused"
    assert project["registry_status"] == "not_registered"
    assert project["runtime_status"] == "not_available"
    assert not (tmp_path / "core" / "agents" / "generated" / "refused_agent.py").exists()


@pytest.mark.asyncio
async def test_validation_failure_never_promotes(tmp_path: Path, monkeypatch):
    builder = make_builder(tmp_path)
    monkeypatch.setattr(
        build_module,
        "validate_agent",
        lambda path: {"ok": False, "error": "invalid_contract"},
    )

    result = await builder.build_from_request("Créer un agent nommé invalid_agent")

    project = result["project"]
    assert project["current_step"] == "validation"
    assert project["validation_status"] == "failed"
    assert project["registry_status"] == "not_registered"
    assert not (tmp_path / "core" / "agents" / "generated" / "invalid_agent.py").exists()


@pytest.mark.asyncio
async def test_test_failure_never_promotes(tmp_path: Path, monkeypatch):
    builder = make_builder(tmp_path)

    def fake_run(command: list[str], name: str) -> dict:
        return {
            "name": name,
            "command": command,
            "returncode": 1 if name == "pytest_agent" else 0,
            "stdout_tail": "test failure" if name == "pytest_agent" else "",
            "stderr_tail": "",
            "ran_at": "2026-06-10T00:00:00+00:00",
        }

    monkeypatch.setattr(builder, "_run_command", fake_run)
    result = await builder.build_from_request("Créer un agent nommé failing_tests_agent")

    project = result["project"]
    assert project["current_step"] == "tests"
    assert project["validation_status"] == "passed"
    assert project["test_status"] == "failed"
    assert project["registry_status"] == "not_registered"
    assert not (tmp_path / "core" / "agents" / "generated" / "failing_tests_agent.py").exists()


@pytest.mark.asyncio
async def test_runtime_failure_rolls_back_promoted_file(tmp_path: Path, monkeypatch):
    builder = make_builder(tmp_path)

    async def failed_verification(spec) -> dict:
        return {"ok": False, "error": "runtime_rejected"}

    monkeypatch.setattr(builder, "_verify_agent", failed_verification)
    result = await builder.build_from_request("Créer un agent nommé runtime_failure_agent")

    project = result["project"]
    assert project["current_step"] == "verification"
    assert project["runtime_status"] == "failed"
    assert project["registry_status"] == "not_registered"
    assert project["registered_agent"] is None
    assert not (tmp_path / "core" / "agents" / "generated" / "runtime_failure_agent.py").exists()
    assert not any("core/agents/generated/" in path for path in project["created_files"])


@pytest.mark.asyncio
async def test_runtime_failure_restores_previous_agent_bytes(tmp_path: Path, monkeypatch):
    builder = make_builder(tmp_path)
    destination = tmp_path / "core" / "agents" / "generated" / "runtime_restore_agent.py"
    destination.parent.mkdir(parents=True)
    previous = b"previous production bytes\n"
    destination.write_bytes(previous)

    async def failed_verification(spec) -> dict:
        return {"ok": False, "error": "runtime_rejected"}

    monkeypatch.setattr(builder, "_verify_agent", failed_verification)
    result = await builder.build_from_request("Créer un agent nommé runtime_restore_agent")

    assert result["status"] == "failed"
    assert destination.read_bytes() == previous


def test_legacy_promoter_obeys_runtime_governor(tmp_path: Path):
    source = tmp_path / "workspace" / "legacy_agent.py"
    source.parent.mkdir(parents=True)
    source.write_text("class Agent:\n    pass\n", encoding="utf-8")

    result = promote_agent(
        str(source),
        generated_dir=tmp_path / "generated",
        runtime_governor=FakeGovernor(False),
    )

    assert result["ok"] is False
    assert result["error"] == "runtime_governor_refused"
    assert not (tmp_path / "generated" / "legacy_agent.py").exists()


def test_runtime_governor_refuses_promotion_in_survival_mode():
    governor = RuntimeGovernor()
    governor.update_from_cognitive_state(
        {
            "runtime_mode": "survival",
            "primary_issue": "runtime_pressure",
        }
    )

    assert governor.authorize_agent_promotion(
        agent_name="blocked_agent",
        requested_by="test",
    ) is False


@pytest.mark.asyncio
async def test_legacy_router_does_not_promote_when_associated_test_fails(
    tmp_path: Path,
    monkeypatch,
):
    workspace_agents = tmp_path / "workspace" / "agents"
    workspace_tests = tmp_path / "workspace" / "agent_tests"
    workspace_agents.mkdir(parents=True)
    workspace_tests.mkdir(parents=True)
    source = workspace_agents / "legacy_tested_agent.py"
    source.write_text(
        "class Agent:\n"
        "    async def execute(self, text=''):\n"
        "        return {'response': text}\n",
        encoding="utf-8",
    )
    (workspace_tests / "test_legacy_tested_agent.py").write_text(
        "def test_failure():\n"
        "    assert False\n",
        encoding="utf-8",
    )

    def forbidden_promotion(*args, **kwargs):
        pytest.fail("promotion must not run after a failed associated test")

    monkeypatch.setattr(agent_router, "WORKSPACE_AGENTS_DIR", workspace_agents)
    monkeypatch.setattr(
        "core.agent_factory.promoter.promote_agent",
        forbidden_promotion,
    )

    response = await agent_router._promote_dynamic_agent(
        "valide l agent legacy_tested"
    )

    assert "Tests échoués" in response


@pytest.mark.asyncio
async def test_goal_status_aggregates_plan_and_build_state(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(persistence, "GOALS_PATH", tmp_path / "data" / "goals_state.json")
    monkeypatch.setattr(goal_manager, "_GOAL_MANAGER", None)
    manager = goal_manager.get_goal_manager()
    goal = manager.create_goal("Créer un agent observable", metadata={"orchestrated": True})
    manager.update_status(goal["id"], "active")

    storage = PlanStorage(tmp_path / "data" / "plans.jsonl")
    storage.save(
        {
            "id": "plan-observable",
            "goal_id": goal["id"],
            "goal": goal["title"],
            "status": "running",
            "current_step": "agent_build",
            "codex_used": True,
        }
    )
    projects = ProjectManager(tmp_path / "data" / "projects.json")
    project = projects.create_project(
        title="Agent observable",
        project_type="agent",
        metadata={
            "goal_id": goal["id"],
            "plan_id": "plan-observable",
            "agent_name": "observable_agent",
            "codex_used": True,
        },
    )
    updated_project = projects.update_project(
        project["project_id"],
        {
            "status": "running",
            "validation_status": "passed",
            "compile_status": "passed",
            "test_status": "passed",
            "governor_status": "allowed",
            "registry_status": "registered",
            "registered_agent": "observable_agent",
            "runtime_status": "pending",
        },
        step="registry",
        step_status="done",
        progress=85,
    )
    assert updated_project is not None

    orchestrator = GoalOrchestrator.__new__(GoalOrchestrator)
    orchestrator.goal_manager = manager
    orchestrator.storage = storage
    orchestrator.agent_build_orchestrator = SimpleNamespace(project_manager=projects)

    payload = orchestrator.get_goal_status(goal["id"])
    assert payload == {
        "goal_id": goal["id"],
        "status": "running",
        "current_step": "registry",
        "progress": 85,
        "plan_id": "plan-observable",
        "project_id": project["project_id"],
        "agent_slug": "observable_agent",
        "codex_used": True,
        "validation_status": "passed",
        "compile_status": "passed",
        "test_status": "passed",
        "governor_status": "allowed",
        "registry_status": "registered",
        "runtime_status": "pending",
        "error": None,
        "errors": [],
        "steps": [
            {
                "name": "registry",
                "status": "done",
                "at": updated_project["steps"][0]["at"],
                "error": None,
            }
        ],
    }

    monkeypatch.setattr(routes, "get_goal_orchestrator", lambda: orchestrator)
    assert await routes.goal_status(goal["id"]) == payload


@pytest.mark.asyncio
async def test_goal_status_returns_404_for_unknown_goal(monkeypatch):
    orchestrator = SimpleNamespace(get_goal_status=lambda goal_id: None)
    monkeypatch.setattr(routes, "get_goal_orchestrator", lambda: orchestrator)

    with pytest.raises(HTTPException) as exc_info:
        await routes.goal_status("missing-goal")

    assert exc_info.value.status_code == 404
