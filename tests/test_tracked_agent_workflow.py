from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

import pytest

from core.agent_factory import build_orchestrator
from core.agent_factory.factory_agent import AgentFactoryAgent
from core.agent_factory.build_orchestrator import AgentBuildOrchestrator
from core.pipeline.routing import agent_router
from core.pipeline.intent.intent_router import Intent, IntentRouter
from core.projects.manager import ProjectManager


@pytest.mark.asyncio
async def test_detects_agent_creation_without_goal():
    result = await IntentRouter().route(
        "Crée un agent qui me donne le temps restant avant la prochaine WWDC d’Apple"
    )
    assert result.intent == Intent.AGENT_CREATION
    assert result.confidence in {"medium", "high"}


@pytest.mark.asyncio
async def test_detects_agent_creation_with_goal():
    result = await IntentRouter().route(
        "/goal Créer un agent qui me donne le temps restant avant la WWDC"
    )
    assert result.intent == Intent.AGENT_CREATION


@pytest.mark.asyncio
async def test_detects_tool_creation_and_project_queries():
    router = IntentRouter()
    tool = await router.route("Ajoute un tool pour calculer un compte à rebours")
    status = await router.route("Où en est le projet WWDC ?")
    listing = await router.route("Liste mes projets")

    assert tool.intent == Intent.TOOL_CREATION
    assert status.intent == Intent.PROJECT_STATUS
    assert listing.intent == Intent.PROJECT_LIST


def test_project_manager_create_update_and_search(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    project = manager.create_project(
        title="Agent compte a rebours WWDC",
        project_type="agent",
        requested_by="test",
        source_channel="api",
        query="Créer un agent WWDC",
    )

    updated = manager.update_project(
        project["project_id"],
        {"status": "running"},
        step="planning",
        step_status="done",
        progress=25,
    )

    assert updated is not None
    assert updated["status"] == "running"
    assert updated["current_step"] == "planning"
    assert updated["progress"] == 25
    assert manager.get_project(project["project_id"])["project_id"] == project["project_id"]
    assert manager.find_project_by_query("WWDC")[0]["project_id"] == project["project_id"]


@pytest.mark.asyncio
async def test_agent_build_creates_validated_registered_project(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    orchestrator = AgentBuildOrchestrator(
        project_manager=manager,
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
    )

    result = await orchestrator.build_from_request(
        "Créer un agent qui me donne le temps restant avant la prochaine WWDC d’Apple",
        requested_by="test",
        source_channel="api",
    )

    project = result["project"]
    assert result["status"] == "completed"
    assert project["status"] == "completed"
    assert project["registry_status"] == "registered"
    assert project["result"]["available"] is True
    assert project["registered_agent"] == "event_countdown_agent"
    assert any(path.endswith("event_countdown_agent.py") for path in project["created_files"])
    assert project["test_results"]
    assert all(item["returncode"] == 0 for item in project["test_results"])
    assert "Projet terminé" in result["response"]
    assert "Tests : OK" in result["response"]
    assert (tmp_path / "core" / "agents" / "generated" / "event_countdown_agent.py").exists()


def test_failed_project_is_not_announced_as_completed(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    orchestrator = AgentBuildOrchestrator(project_manager=manager, project_root=tmp_path, runtime_check=False)
    project = manager.create_project(
        title="Agent cassé",
        project_type="agent",
        requested_by="test",
        source_channel="api",
        query="Créer un agent cassé",
    )
    failed = manager.update_project(
        project["project_id"],
        {
            "status": "failed",
            "current_step": "tests",
            "error": "pytest failed",
            "result": {"available": False},
            "registry_status": "not_registered",
        },
        step="tests",
        step_status="failed",
        error="pytest failed",
    )

    text = orchestrator.format_project_response(failed)
    assert "Projet échoué" in text
    assert "Projet terminé" not in text
    assert "Agent enregistré : oui" not in text


def test_completed_message_requires_registry_proof(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    orchestrator = AgentBuildOrchestrator(project_manager=manager, project_root=tmp_path, runtime_check=False)
    project = manager.create_project(
        title="Agent sans registre",
        project_type="agent",
        requested_by="test",
        source_channel="api",
        query="Créer un agent sans registre",
    )
    completed_without_registry = manager.update_project(
        project["project_id"],
        {
            "status": "completed",
            "current_step": "completed",
            "result": {"agent": "ghost_agent", "available": True},
            "test_results": [{"returncode": 0}],
            "registry_status": "not_registered",
        },
    )

    text = orchestrator.format_project_response(completed_without_registry)
    assert "Projet terminé" not in text
    assert "Agent enregistré : oui" not in text
    assert "Statut : completed" in text


@pytest.mark.asyncio
async def test_agent_build_does_not_require_obsidian(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    orchestrator = AgentBuildOrchestrator(
        project_manager=manager,
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
    )

    result = await orchestrator.build_from_request("J’aimerais un agent qui surveille la météo")

    created_files = result["project"]["created_files"]
    assert result["status"] == "completed"
    assert not any("obsidian" in path.lower() for path in created_files)


def test_build_orchestrator_has_no_obsidian_dependency():
    source = inspect.getsource(build_orchestrator)
    assert "obsidian" not in source.lower()


def test_planner_produces_specs_without_execution_side_effects():
    from core.planning.planner import AutonomousPlanner

    plan = AutonomousPlanner().create_plan("Créer un agent météo")
    data = plan.to_dict()

    assert data["status"] == "pending"
    assert data["steps"]
    assert all(step["status"] == "pending" for step in data["steps"])
    assert all(step.get("result") is None for step in data["steps"])
    assert "executed_at" not in data
    assert "agent_creation_proposal" not in data


def test_agent_creation_dispatch_has_single_primary_handler():
    source = inspect.getsource(agent_router.AgentRouter.route)
    assert source.count("Intent.AGENT_CREATION") == 1
    assert "_get_agent_factory().execute" not in source
    assert "_build_tracked_agent" in source


@pytest.mark.asyncio
async def test_agent_creation_dispatch_uses_build_orchestrator(monkeypatch):
    calls: list[tuple[str, str, str]] = []

    class FakeModel:
        def set_last_intent(self, *_args):
            return None

        def add_recent_activity(self, *_args):
            return None

    class FakeOrchestrator:
        async def build_from_request(self, query: str, *, requested_by: str, source_channel: str):
            calls.append((query, requested_by, source_channel))
            return {"status": "completed", "response": "orchestrated"}

        def format_project_response(self, project):
            return "formatted"

    async def forbidden_factory(*_args, **_kwargs):
        raise AssertionError("legacy AgentFactoryAgent must not handle agent_creation")

    monkeypatch.setattr(agent_router, "_get_self_model", lambda: FakeModel())
    monkeypatch.setattr(build_orchestrator, "AgentBuildOrchestrator", FakeOrchestrator)
    monkeypatch.setattr(AgentFactoryAgent, "execute", forbidden_factory)

    result = await agent_router.AgentRouter().route(
        type("IntentLike", (), {"intent": Intent.AGENT_CREATION, "confidence": "high"})(),
        "Créer un agent de test",
    )

    assert result == "orchestrated"
    assert calls == [("Créer un agent de test", "user", "api")]


@pytest.mark.asyncio
async def test_legacy_agent_factory_delegates_to_build_orchestrator(monkeypatch):
    from core.agent_factory import factory_agent

    class FakeOrchestrator:
        async def build_from_request(self, query: str, *, requested_by: str, source_channel: str):
            return {
                "status": "completed",
                "response": f"built:{query}",
                "project": {
                    "project_id": "project-1",
                    "status": "completed",
                    "registry_status": "registered",
                    "created_files": ["core/agents/generated/test_agent.py"],
                },
            }

    monkeypatch.setattr(factory_agent, "AgentBuildOrchestrator", FakeOrchestrator)

    result = await AgentFactoryAgent().execute("Créer un agent de test")

    assert result.success is True
    assert result.content == "built:Créer un agent de test"
    assert result.metadata["compatibility_facade"] is True
    assert result.metadata["orchestrator"] == "AgentBuildOrchestrator"


@pytest.mark.asyncio
async def test_project_routes_list_get_and_search(monkeypatch, tmp_path: Path):
    from core.projects import routes

    manager = ProjectManager(tmp_path / "projects.json")
    project = manager.create_project(
        title="Agent compte a rebours WWDC",
        project_type="agent",
        requested_by="test",
        source_channel="api",
        query="Créer un agent WWDC",
    )
    monkeypatch.setattr(routes, "get_project_manager", lambda: manager)

    listed = await routes.list_projects()
    fetched = await routes.get_project(project["project_id"])
    searched = await routes.search_projects("WWDC")

    assert listed["count"] == 1
    assert fetched["project"]["project_id"] == project["project_id"]
    assert searched["projects"][0]["project_id"] == project["project_id"]
