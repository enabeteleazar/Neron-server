from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.agent_factory import build_orchestrator
from core.agent_factory.agent_creator import AgentCreator
from core.agent_factory.agent_manager import AgentManager
from core.agent_factory.factory_agent import AgentFactoryAgent
from core.agent_factory.build_orchestrator import AgentBuildOrchestrator
from core.agent_factory.registry import DynamicAgentRegistry
from core.agent_factory.registry_scanner import AgentRegistryScanner
from core.agents.conversation.conversation_agent import ConversationAgent
from core.events import event_types
from core.events.event_bus import event_bus
from core.evolution.models import CommandResult
from core.pipeline.routing import agent_router
from core.pipeline.intent.intent_router import Intent, IntentRouter
from core.pipeline.intent.intent_router import IntentResult
from core.projects.manager import ProjectManager
from core.runtime.agents.agent_runtime_manager import AgentRuntimeManager


class FakeCodexRunner:
    def __init__(
        self,
        *,
        agent_file: Path | None = None,
        agent_name: str = "demo_agent",
        agent_code: str | None = None,
        codex_returncode: int = 0,
        tests_returncode: int = 0,
    ) -> None:
        self.prompts: list[str] = []
        self.run_ids: list[str] = []
        self.tests_calls = 0
        self.commit_calls = 0
        self.agent_file = agent_file
        self.agent_name = agent_name
        self.agent_code = agent_code
        self.codex_returncode = codex_returncode
        self.tests_returncode = tests_returncode

    async def run_codex(self, prompt: str, run_id: str) -> CommandResult:
        self.prompts.append(prompt)
        self.run_ids.append(run_id)
        if self.codex_returncode == 0 and self.agent_file is not None:
            self.agent_file.parent.mkdir(parents=True, exist_ok=True)
            self.agent_file.write_text(
                self.agent_code
                if self.agent_code is not None
                else _valid_agent_code(self.agent_name),
                encoding="utf-8",
            )
        return CommandResult(
            "codex",
            ["codex", "exec"],
            self.codex_returncode,
            stdout="codex ok" if self.codex_returncode == 0 else "",
            stderr="" if self.codex_returncode == 0 else "codex failed",
        )

    async def run_tests(self) -> list[CommandResult]:
        self.tests_calls += 1
        return [
            CommandResult(
                "pytest",
                ["pytest"],
                self.tests_returncode,
                stdout="tests ok" if self.tests_returncode == 0 else "",
                stderr="" if self.tests_returncode == 0 else "tests failed",
            )
        ]

    async def commit_and_push(self, message: str) -> dict:
        self.commit_calls += 1
        return {"ok": True, "message": message}


class FakeAgentBuilderCodexRunner:
    def __init__(
        self,
        *,
        returncode: int = 0,
        write_files: bool = True,
        generated_dir: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.returncode = returncode
        self.write_files = write_files
        self.generated_dir = generated_dir
        self.project_root = project_root or Path.cwd()
        self.calls: list[tuple[str, str]] = []

    async def run_codex(self, prompt: str, run_id: str) -> CommandResult:
        self.calls.append((prompt, run_id))
        if self.generated_dir is not None:
            self.generated_dir.mkdir(parents=True, exist_ok=True)
            (self.generated_dir / "codex_direct_write_agent.py").write_text(
                _valid_agent_code("codex_direct_write_agent"),
                encoding="utf-8",
            )
        if self.returncode == 0 and self.write_files:
            agent_file = self._path_from_prompt(prompt, "Write the agent only at ")
            test_file = self._path_from_prompt(prompt, "Write the test only at ")
            agent_name = agent_file.stem
            agent_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.parent.mkdir(parents=True, exist_ok=True)
            agent_file.write_text(_valid_agent_code(agent_name), encoding="utf-8")
            test_file.write_text(self._valid_agent_test(agent_file), encoding="utf-8")
        return CommandResult(
            "codex",
            ["codex", "exec", "prompt"],
            self.returncode,
            stdout="codex ok" if self.returncode == 0 else "",
            stderr="" if self.returncode == 0 else "codex failed",
        )

    def _path_from_prompt(self, prompt: str, prefix: str) -> Path:
        for line in prompt.splitlines():
            if prefix in line:
                path = Path(line.split(prefix, 1)[1].rstrip("."))
                return path if path.is_absolute() else self.project_root / path
        raise AssertionError(f"missing path prefix: {prefix}")

    def _valid_agent_test(self, agent_file: Path) -> str:
        return "\n".join(
            [
                "from __future__ import annotations",
                "import importlib.util",
                "import pytest",
                f"AGENT_FILE = {str(agent_file)!r}",
                "",
                "def load_agent():",
                "    spec = importlib.util.spec_from_file_location('agent_under_test', AGENT_FILE)",
                "    module = importlib.util.module_from_spec(spec)",
                "    assert spec and spec.loader",
                "    spec.loader.exec_module(module)",
                "    return module.Agent()",
                "",
                "@pytest.mark.asyncio",
                "async def test_agent_execute_returns_response():",
                "    result = await load_agent().execute(text='hello')",
                "    assert result['status'] == 'ok'",
                "    assert result['response']",
                "",
            ]
        )


def _valid_agent_code(agent_name: str) -> str:
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "class Agent:",
            f"    name = {agent_name!r}",
            "",
            "    async def execute(self, text: str = '') -> dict:",
            "        return {'status': 'ok', 'response': f'response for {text}'}",
            "",
        ]
    )


class FakeRuntimeManager:
    def __init__(self, generated_agents: Path) -> None:
        self.registry = DynamicAgentRegistry(generated_agents)
        self.reload_calls = 0

    def reload(self) -> dict:
        self.reload_calls += 1
        agents = sorted((self.registry.load_generated_agents() or {}).keys())
        return {"ok": True, "count": len(agents), "agents": agents}

    def get_state(self, name: str):
        return {"name": name, "runs": 0}


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


def test_project_manager_diagnoses_recent_failed_projects(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")

    codex_project = manager.create_project(
        title="Diagnostiquer les projets en échec",
        project_type="evolution",
        requested_by="test",
        source_channel="api",
        query="3 projets failed récents",
    )
    manager.update_project(codex_project["project_id"], {"status": "running"}, step="accepted")
    manager.update_project(codex_project["project_id"], {"status": "running"}, step="codex_running")
    manager.update_project(
        codex_project["project_id"],
        {"status": "failed", "current_step": "failed"},
        step="failed",
        step_status="failed",
        error="Codex a échoué.",
    )

    tests_project = manager.create_project(
        title="Agent tests cassés",
        project_type="agent",
        requested_by="test",
        source_channel="api",
        query="Créer un agent cassé",
    )
    manager.update_project(
        tests_project["project_id"],
        {
            "status": "failed",
            "current_step": "tests",
            "test_results": [{"name": "pytest_agent", "returncode": 1, "stderr_tail": "pytest failed"}],
        },
        step="tests",
        step_status="failed",
        error="pytest failed",
    )

    compile_project = manager.create_project(
        title="Agent syntaxe cassée",
        project_type="agent",
        requested_by="test",
        source_channel="api",
        query="Créer un agent invalide",
    )
    manager.update_project(
        compile_project["project_id"],
        {"status": "failed", "current_step": "compile"},
        step="compile",
        step_status="failed",
        error="py_compile failed",
    )

    report = manager.diagnose_recent_failures(limit=3)

    categories = {item["category"]: item["count"] for item in report["categories"]}
    by_id = {item["project_id"]: item for item in report["projects"]}
    assert report["count"] == 3
    assert categories == {
        "compile_failed": 1,
        "tests_failed": 1,
        "codex_execution_failed": 1,
    }
    assert by_id[codex_project["project_id"]]["last_completed_step"] == "codex_running"
    assert by_id[codex_project["project_id"]]["retry_requires_validation"] is True
    assert "Aucune relance automatique" in report["summary"]

    text = manager.format_failure_report(limit=3)
    assert "Diagnostic projets failed récents" in text
    assert "Relance automatique : non" in text


def test_project_manager_enriches_evolution_failures_from_run_state(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    project = manager.create_project(
        title="Evolution Codex",
        project_type="evolution",
        requested_by="test",
        source_channel="api",
        query="Faire évoluer Néron",
    )
    manager.update_project(project["project_id"], {"status": "running"}, step="accepted")
    manager.update_project(project["project_id"], {"status": "running"}, step="codex_running")
    manager.update_project(
        project["project_id"],
        {"status": "failed", "current_step": "failed"},
        step="failed",
        step_status="failed",
        error="Codex a échoué.",
    )
    (tmp_path / "evolution_state.json").write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "run_id": "evo_run_1",
                        "project_id": project["project_id"],
                        "status": "failed",
                        "current_step": "failed",
                        "error": "Codex a échoué.",
                        "updated_at": "2026-06-02T10:00:00+00:00",
                        "codex": {
                            "name": "codex",
                            "returncode": 2,
                            "stderr": "error: unexpected argument '--ask-for-approval' found",
                            "stdout": "",
                            "timed_out": False,
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = manager.diagnose_recent_failures(limit=1)

    diagnostic = report["projects"][0]
    assert diagnostic["category"] == "codex_cli_arguments"
    assert diagnostic["related_run_id"] == "evo_run_1"
    assert any("codex_returncode=2" in item for item in diagnostic["evidence"])
    assert diagnostic["retry_requires_validation"] is True


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


@pytest.mark.asyncio
async def test_agent_build_deduplicates_wwdc_apostrophe_variants(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    orchestrator = AgentBuildOrchestrator(
        project_manager=manager,
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
    )

    first = await orchestrator.build_from_request(
        "Crée un agent qui me donne le temps restant avant la prochaine WWDC d Apple"
    )
    second = await orchestrator.build_from_request(
        "Crée un agent qui me donne le temps restant avant la prochaine WWDC d’Apple"
    )

    projects = manager.list_projects(limit=10)
    assert len(projects) == 1
    assert first["project"]["project_id"] == second["project"]["project_id"]
    assert second["reused_existing_project"] is True
    assert "Agent déjà disponible : event_countdown_agent" in second["response"]
    assert f"Projet existant : {first['project']['project_id']}" in second["response"]
    assert "Tests déjà validés : OK" in second["response"]
    assert "Aucune reconstruction nécessaire" in second["response"]
    assert "Agent créé" not in second["response"]


@pytest.mark.asyncio
async def test_repeated_agent_build_returns_reused_existing_project(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    orchestrator = AgentBuildOrchestrator(
        project_manager=manager,
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
    )

    query = "Créer un agent qui me donne le temps restant avant la prochaine WWDC d’Apple"
    first = await orchestrator.build_from_request(query)
    second = await orchestrator.build_from_request(query)

    assert first["reused_existing_project"] is False
    assert second["reused_existing_project"] is True
    assert second["project"]["project_id"] == first["project"]["project_id"]
    assert second["build_executed"] is False
    assert "Agent créé" not in second["response"]


def test_completed_project_current_step_is_completed(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    project = manager.create_project(
        title="Agent finalisé",
        project_type="agent",
        requested_by="test",
        source_channel="api",
        query="Créer un agent finalisé",
    )

    completed = manager.update_project(
        project["project_id"],
        {"status": "completed"},
        step="verification",
        step_status="done",
        progress=100,
    )

    assert completed["status"] == "completed"
    assert completed["current_step"] == "completed"


def test_dynamic_agent_registry_finds_registered_agent_by_spec(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    orchestrator = AgentBuildOrchestrator(
        project_manager=manager,
        project_root=tmp_path,
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
    )
    spec = orchestrator.plan_spec(
        "Créer un agent qui me donne le temps restant avant la prochaine WWDC d’Apple"
    )
    generated_agents = tmp_path / "core" / "agents" / "generated"
    generated_agents.mkdir(parents=True)
    registered_agent = generated_agents / "event_countdown_agent.py"
    registered_agent.write_text(
        f"AGENT_SPEC = {json.dumps(spec.to_dict(), sort_keys=True)}\n"
        f"AGENT_SPEC_SIGNATURE = {orchestrator._spec_signature(spec)!r}\n"
        "class Agent:\n"
        "    name = 'event_countdown_agent'\n"
        "    async def execute(self, text=''):\n"
        "        return {'status': 'ok', 'response': 'available'}\n",
        encoding="utf-8",
    )

    match = DynamicAgentRegistry(generated_agents).find_registered_agent_for_spec(
        spec.to_dict(),
        orchestrator._spec_signature(spec),
    )

    assert match is not None
    assert match["agent_name"] == "event_countdown_agent"
    assert match["path"] == str(registered_agent)


@pytest.mark.asyncio
async def test_agent_registry_scanner_registers_valid_agent_and_reloads_runtime(tmp_path: Path):
    generated = tmp_path / "core" / "agents" / "generated"
    generated.mkdir(parents=True)
    agent_file = generated / "scan_valid_agent.py"
    agent_file.write_text(_valid_agent_code("scan_valid_agent"), encoding="utf-8")
    runtime = FakeRuntimeManager(generated)
    scanner = AgentRegistryScanner(
        generated_agents=generated,
        index_path=tmp_path / "data" / "agent_registry_index.json",
        runtime_manager=runtime,
    )

    result = await scanner.scan()
    index = scanner.get_index()
    entry = index["agents"]["scan_valid_agent"]

    assert result["status"] == "ok"
    assert result["scanned"] == 1
    assert result["active"] == 1
    assert result["invalid"] == 0
    assert result["runtime_reloaded"] is True
    assert runtime.reload_calls == 1
    assert result["runtime_reload"]["agents"] == ["scan_valid_agent"]
    assert entry["agent_name"] == "scan_valid_agent"
    assert entry["path"] == str(agent_file)
    assert entry["status"] == "active"
    assert entry["validation_ok"] is True
    assert entry["error"] is None
    assert entry["source"] == "generated_scan"
    assert entry["checksum"]
    assert entry["last_scanned_at"]


@pytest.mark.asyncio
async def test_agent_registry_scanner_marks_invalid_agent_without_runtime_reload(tmp_path: Path):
    generated = tmp_path / "core" / "agents" / "generated"
    generated.mkdir(parents=True)
    invalid = generated / "scan_invalid_agent.py"
    invalid.write_text(
        "class Agent:\n"
        "    name = 'scan_invalid_agent'\n"
        "    def execute(self, text=''):\n"
        "        return {'status': 'ok'}\n",
        encoding="utf-8",
    )
    runtime = FakeRuntimeManager(generated)
    scanner = AgentRegistryScanner(
        generated_agents=generated,
        index_path=tmp_path / "data" / "agent_registry_index.json",
        runtime_manager=runtime,
    )

    result = await scanner.scan()
    index = scanner.get_index()
    entry = index["agents"]["scan_invalid_agent"]

    assert result["status"] == "ok"
    assert result["active"] == 0
    assert result["invalid"] == 1
    assert result["runtime_reloaded"] is False
    assert result["runtime_reload"] is None
    assert runtime.reload_calls == 0
    assert entry["status"] == "invalid"
    assert entry["validation_ok"] is False
    assert "execute" in entry["error"]
    assert "scan_invalid_agent" not in DynamicAgentRegistry(generated).load_generated_agents()
    assert invalid.exists()


def test_agent_manager_status_and_inspect_registered_agent(tmp_path: Path):
    generated = tmp_path / "core" / "agents" / "generated"
    generated.mkdir(parents=True)
    agent_file = generated / "managed_demo_agent.py"
    agent_file.write_text(_valid_agent_code("managed_demo_agent"), encoding="utf-8")
    manager = AgentManager(
        generated_agents=generated,
        backups_dir=tmp_path / "data" / "agent_backups",
        runtime_manager=FakeRuntimeManager(generated),
    )

    listing = manager.list_managed_agents()
    status = manager.get_agent_status("managed_demo_agent")
    inspection = manager.inspect_agent("managed_demo_agent")

    assert listing["count"] == 1
    assert listing["agents"][0]["agent"] == "managed_demo_agent"
    assert status["status"] == "ok"
    assert status["validation"]["ok"] is True
    assert status["protected"] is False
    assert inspection["contains_agent_class"] is True
    assert inspection["contains_execute"] is True
    assert "class Agent" in inspection["source_preview"]


def test_agent_manager_delete_requires_backup_and_reloads_runtime(tmp_path: Path):
    generated = tmp_path / "core" / "agents" / "generated"
    generated.mkdir(parents=True)
    agent_file = generated / "managed_delete_agent.py"
    agent_file.write_text(_valid_agent_code("managed_delete_agent"), encoding="utf-8")
    runtime = FakeRuntimeManager(generated)
    manager = AgentManager(
        generated_agents=generated,
        backups_dir=tmp_path / "data" / "agent_backups",
        runtime_manager=runtime,
    )

    result = manager.delete_agent("managed_delete_agent")

    assert result["status"] == "deleted"
    assert result["deleted"] is True
    assert result["backup"]["backup_created"] is True
    assert Path(result["backup"]["backup_path"]).exists()
    assert not agent_file.exists()
    assert result["runtime_reload"]["ok"] is True
    assert runtime.reload_calls == 1


def test_agent_manager_refuses_delete_for_protected_agent(tmp_path: Path):
    generated = tmp_path / "core" / "agents" / "generated"
    generated.mkdir(parents=True)
    protected = generated / "event_countdown_agent.py"
    protected.write_text(_valid_agent_code("event_countdown_agent"), encoding="utf-8")
    runtime = FakeRuntimeManager(generated)
    manager = AgentManager(
        generated_agents=generated,
        backups_dir=tmp_path / "data" / "agent_backups",
        runtime_manager=runtime,
    )

    result = manager.delete_agent("event_countdown_agent")

    assert result["status"] == "refused"
    assert result["reason"] == "protected_agent"
    assert protected.exists()
    assert not (tmp_path / "data" / "agent_backups" / "event_countdown_agent").exists()
    assert runtime.reload_calls == 0


def test_agent_creator_respects_explicit_agent_name(tmp_path: Path):
    creator = AgentCreator(
        proposals_path=tmp_path / "agent_creator_proposals.jsonl",
        project_root=tmp_path,
    )

    proposal = creator.request_agent_creation(
        goal="Créer un brouillon d’agent nommé audit_agent_test pour auditer les plans.",
        plan={"id": "plan-1", "goal_id": "goal-1"},
    )

    assert proposal["agent_name"] == "audit_agent_test"
    assert proposal["goal"] == "Créer un brouillon d’agent nommé audit_agent_test pour auditer les plans."
    assert proposal["proposed_files"] == [
        "workspace/agents/audit_agent_test.py",
        "tests/test_audit_agent_test.py",
    ]


@pytest.mark.parametrize(
    ("goal", "expected_agent_name"),
    [
        ("Créer un brouillon d’agent de test nommé audit_agent_test", "audit_agent_test"),
        ("Créer un agent appelé maison_agent", "maison_agent"),
        ("Create an agent named demo_agent", "demo_agent"),
        ("Créer un agent météo spécialisé agriculture", "agriculture_weather_agent"),
        ("Créer un agent météo", "weather_agent"),
    ],
)
def test_agent_creator_name_inference_prioritizes_explicit_names(
    tmp_path: Path,
    goal: str,
    expected_agent_name: str,
):
    creator = AgentCreator(
        proposals_path=tmp_path / "agent_creator_proposals.jsonl",
        project_root=tmp_path,
    )

    proposal = creator.request_agent_creation(
        goal=goal,
        plan={"id": f"plan-{expected_agent_name}", "goal_id": "goal-name"},
    )

    assert proposal["agent_name"] == expected_agent_name


@pytest.mark.asyncio
async def test_agent_proposal_approval_builds_registers_and_reloads_runtime(monkeypatch, tmp_path: Path):
    from core.projects import routes

    data_dir = tmp_path / "data"
    project_root = tmp_path / "project"
    generated_agents = project_root / "core" / "agents" / "generated"

    creator = AgentCreator(
        proposals_path=data_dir / "agent_creator_proposals.jsonl",
        project_root=project_root,
    )
    proposal = creator.request_agent_creation(
        goal="Créer un brouillon d’agent nommé audit_agent_test pour auditer les plans.",
        plan={"id": "plan-approval", "goal_id": "goal-approval"},
    )
    manager = ProjectManager(data_dir / "projects.json")
    orchestrator = AgentBuildOrchestrator(
        project_manager=manager,
        project_root=project_root,
        workspace_agents=project_root / "workspace" / "agents",
        workspace_tests=project_root / "workspace" / "agent_tests",
        generated_agents=generated_agents,
        runtime_check=False,
    )
    runtime = AgentRuntimeManager()
    runtime.registry = DynamicAgentRegistry(generated_agents)

    monkeypatch.setattr(routes, "AgentCreator", lambda: creator)
    monkeypatch.setattr(routes, "AgentBuildOrchestrator", lambda: orchestrator)
    monkeypatch.setattr(routes, "get_agent_runtime_manager", lambda: runtime)

    result = await routes.approve_agent_proposal(proposal["agent_request_id"])

    assert result["agent_request_id"] == proposal["agent_request_id"]
    assert result["mode"] == "deterministic"
    assert result["proposal_status"] == "human_approved"
    assert result["build_status"] == "completed"
    assert result["registered_agent"] == "audit_agent_test"
    assert result["errors"] == []
    assert "audit_agent_test" in result["runtime_reload"]["agents"]
    assert any(path.endswith("workspace/agents/audit_agent_test.py") for path in result["created_files"])
    assert any(path.endswith("workspace/agent_tests/test_audit_agent_test.py") for path in result["created_files"])
    assert any(path.endswith("core/agents/generated/audit_agent_test.py") for path in result["created_files"])
    assert (generated_agents / "audit_agent_test.py").exists()
    assert "audit_agent_test" in runtime.list_agents()

    updated = creator.get_proposal(proposal["agent_request_id"])
    assert updated is not None
    assert updated["status"] == "human_approved"
    assert updated["build_status"] == "completed"
    assert updated["registered_agent"] == "audit_agent_test"
    assert updated["applied_to_core"] is True


@pytest.mark.asyncio
async def test_agent_proposal_approval_accepts_explicit_deterministic_mode(monkeypatch, tmp_path: Path):
    from core.projects import routes

    data_dir = tmp_path / "data"
    project_root = tmp_path / "project"
    generated_agents = project_root / "core" / "agents" / "generated"
    creator = AgentCreator(
        proposals_path=data_dir / "agent_creator_proposals.jsonl",
        project_root=project_root,
    )
    proposal = creator.request_agent_creation(
        goal="Créer un agent appelé maison_agent",
        plan={"id": "plan-deterministic-mode", "goal_id": "goal-deterministic-mode"},
    )
    orchestrator = AgentBuildOrchestrator(
        project_manager=ProjectManager(data_dir / "projects.json"),
        project_root=project_root,
        workspace_agents=project_root / "workspace" / "agents",
        workspace_tests=project_root / "workspace" / "agent_tests",
        generated_agents=generated_agents,
        runtime_check=False,
    )
    runtime = AgentRuntimeManager()
    runtime.registry = DynamicAgentRegistry(generated_agents)

    monkeypatch.setattr(routes, "AgentCreator", lambda: creator)
    monkeypatch.setattr(routes, "AgentBuildOrchestrator", lambda: orchestrator)
    monkeypatch.setattr(routes, "get_agent_runtime_manager", lambda: runtime)

    result = await routes.approve_agent_proposal(
        proposal["agent_request_id"],
        routes.AgentProposalApprovalRequest(mode="deterministic"),
    )

    assert result["mode"] == "deterministic"
    assert result["build_status"] == "completed"
    assert result["registered_agent"] == "maison_agent"
    assert "maison_agent" in result["runtime_reload"]["agents"]


@pytest.mark.asyncio
async def test_agent_proposal_approval_codex_mode_calls_codex_runner(monkeypatch, tmp_path: Path):
    from core.projects import routes

    data_dir = tmp_path / "data"
    project_root = tmp_path / "project"
    generated_agents = project_root / "core" / "agents" / "generated"
    creator = AgentCreator(
        proposals_path=data_dir / "agent_creator_proposals.jsonl",
        project_root=project_root,
    )
    proposal = creator.request_agent_creation(
        goal="Create an agent named demo_agent",
        plan={"id": "plan-codex-mode", "goal_id": "goal-codex-mode"},
    )
    runner = FakeCodexRunner(
        agent_file=project_root / "workspace" / "agents" / "demo_agent.py",
        agent_name="demo_agent",
    )
    runtime = AgentRuntimeManager()
    runtime.registry = DynamicAgentRegistry(generated_agents)

    monkeypatch.setattr(routes, "AgentCreator", lambda: creator)
    monkeypatch.setattr(routes, "CodexRunner", lambda: runner)
    monkeypatch.setattr(routes, "get_agent_runtime_manager", lambda: runtime)

    result = await routes.approve_agent_proposal(
        proposal["agent_request_id"],
        routes.AgentProposalApprovalRequest(mode="codex"),
    )

    assert result["mode"] == "codex"
    assert result["proposal_status"] == "human_approved"
    assert result["codex_result"]["ok"] is True
    assert result["test_results"][0]["ok"] is True
    assert result["registered_agent"] == "demo_agent"
    assert "demo_agent" in result["runtime_reload"]["agents"]
    assert any(path.endswith("workspace/agents/demo_agent.py") for path in result["created_files"])
    assert any(path.endswith("core/agents/generated/demo_agent.py") for path in result["created_files"])
    assert (generated_agents / "demo_agent.py").exists()
    assert result["errors"] == []
    assert runner.run_ids == [f"agent_creator_{proposal['agent_request_id']}"]
    assert "demo_agent" in runner.prompts[0]
    assert "Ne fais aucun commit" in runner.prompts[0]
    assert runner.tests_calls == 1
    assert runner.commit_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("codex_returncode", "tests_returncode", "expected_error", "expected_tests_calls"),
    [
        (1, 0, "codex failed", 0),
        (0, 1, "tests failed", 1),
    ],
)
async def test_agent_proposal_approval_codex_mode_does_not_promote_on_codex_or_test_failure(
    monkeypatch,
    tmp_path: Path,
    codex_returncode: int,
    tests_returncode: int,
    expected_error: str,
    expected_tests_calls: int,
):
    from core.projects import routes

    data_dir = tmp_path / "data"
    project_root = tmp_path / "project"
    generated_agents = project_root / "core" / "agents" / "generated"
    creator = AgentCreator(
        proposals_path=data_dir / "agent_creator_proposals.jsonl",
        project_root=project_root,
    )
    proposal = creator.request_agent_creation(
        goal="Create an agent named demo_agent",
        plan={
            "id": f"plan-codex-failure-{codex_returncode}-{tests_returncode}",
            "goal_id": "goal-codex-failure",
        },
    )
    runner = FakeCodexRunner(
        agent_file=project_root / "workspace" / "agents" / "demo_agent.py",
        agent_name="demo_agent",
        codex_returncode=codex_returncode,
        tests_returncode=tests_returncode,
    )
    runtime = AgentRuntimeManager()
    runtime.registry = DynamicAgentRegistry(generated_agents)

    monkeypatch.setattr(routes, "AgentCreator", lambda: creator)
    monkeypatch.setattr(routes, "CodexRunner", lambda: runner)
    monkeypatch.setattr(routes, "get_agent_runtime_manager", lambda: runtime)

    result = await routes.approve_agent_proposal(
        proposal["agent_request_id"],
        routes.AgentProposalApprovalRequest(mode="codex"),
    )

    assert result["mode"] == "codex"
    assert result["registered_agent"] is None
    assert result["runtime_reload"] is None
    assert expected_error in result["errors"][0]
    assert not (generated_agents / "demo_agent.py").exists()
    assert runner.tests_calls == expected_tests_calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("agent_file_enabled", "agent_code", "expected_error"),
    [
        (False, None, "agent_file_missing"),
        (True, "class Agent:\n    pass\n", "méthode execute manquante"),
    ],
)
async def test_agent_proposal_approval_codex_mode_does_not_promote_missing_or_invalid_agent(
    monkeypatch,
    tmp_path: Path,
    agent_file_enabled: bool,
    agent_code: str | None,
    expected_error: str,
):
    from core.projects import routes

    data_dir = tmp_path / "data"
    project_root = tmp_path / "project"
    generated_agents = project_root / "core" / "agents" / "generated"
    creator = AgentCreator(
        proposals_path=data_dir / "agent_creator_proposals.jsonl",
        project_root=project_root,
    )
    proposal = creator.request_agent_creation(
        goal="Create an agent named demo_agent",
        plan={
            "id": f"plan-codex-invalid-{agent_file_enabled}",
            "goal_id": "goal-codex-invalid",
        },
    )
    runner = FakeCodexRunner(
        agent_file=(
            project_root / "workspace" / "agents" / "demo_agent.py"
            if agent_file_enabled
            else None
        ),
        agent_name="demo_agent",
        agent_code=agent_code,
    )
    runtime = AgentRuntimeManager()
    runtime.registry = DynamicAgentRegistry(generated_agents)

    monkeypatch.setattr(routes, "AgentCreator", lambda: creator)
    monkeypatch.setattr(routes, "CodexRunner", lambda: runner)
    monkeypatch.setattr(routes, "get_agent_runtime_manager", lambda: runtime)

    result = await routes.approve_agent_proposal(
        proposal["agent_request_id"],
        routes.AgentProposalApprovalRequest(mode="codex"),
    )

    assert result["registered_agent"] is None
    assert result["runtime_reload"] is None
    assert expected_error in result["errors"][0]
    assert not (generated_agents / "demo_agent.py").exists()


def test_agent_proposal_approval_rejects_unknown_mode():
    from core.projects import routes

    with pytest.raises(ValidationError):
        routes.AgentProposalApprovalRequest(mode="unknown")


@pytest.mark.asyncio
async def test_agent_proposal_approval_codex_mode_refuses_when_not_codex_ready(monkeypatch, tmp_path: Path):
    from fastapi import HTTPException
    from core.projects import routes

    data_dir = tmp_path / "data"
    creator = AgentCreator(
        proposals_path=data_dir / "agent_creator_proposals.jsonl",
        project_root=tmp_path / "project",
    )
    proposal = creator.request_agent_creation(
        goal="Create an agent named demo_agent",
        plan={"id": "plan-codex-not-ready", "goal_id": "goal-codex-not-ready"},
    )
    creator.update_proposal(proposal["agent_request_id"], {"codex_ready": False})
    runner = FakeCodexRunner()

    monkeypatch.setattr(routes, "AgentCreator", lambda: creator)
    monkeypatch.setattr(routes, "CodexRunner", lambda: runner)

    with pytest.raises(HTTPException) as exc_info:
        await routes.approve_agent_proposal(
            proposal["agent_request_id"],
            routes.AgentProposalApprovalRequest(mode="codex"),
        )

    assert exc_info.value.status_code == 409
    assert "codex_ready" in str(exc_info.value.detail)
    assert creator.get_proposal(proposal["agent_request_id"])["status"] == "pending_human_validation"
    assert runner.prompts == []


@pytest.mark.asyncio
async def test_conversation_agent_discovers_and_runs_matching_registered_agent(tmp_path: Path):
    generated_agents = tmp_path / "core" / "agents" / "generated"
    generated_agents.mkdir(parents=True)
    (generated_agents / "event_countdown_agent.py").write_text(
        "class Agent:\n"
        "    name = 'event_countdown_agent'\n"
        "    target_event = 'WWDC'\n"
        "    source = 'static Apple WWDC countdown'\n"
        "    async def execute(self, text=''):\n"
        "        return {'status': 'ok', 'response': 'Temps restant avant la WWDC : 5 jours'}\n",
        encoding="utf-8",
    )

    result = await ConversationAgent(
        registry=DynamicAgentRegistry(generated_agents)
    ).delegate_to_registered_agent("Combien de temps reste-t-il avant la WWDC ?")

    assert result is not None
    assert result["ok"] is True
    assert result["agent"] == "event_countdown_agent"
    assert result["response"] == "Temps restant avant la WWDC : 5 jours"


@pytest.mark.asyncio
async def test_agent_router_routes_conversation_to_registered_agent_before_llm(monkeypatch):
    class FakeModel:
        def set_last_intent(self, *_args):
            return None

        def add_recent_activity(self, *_args):
            return None

        def set_last_agent(self, *_args):
            return None

        def set_last_action(self, *_args):
            return None

        def set_last_decision(self, *_args):
            return None

        def set_last_reasoning(self, *_args):
            return None

        def set_last_error(self, *_args):
            return None

    class ForbiddenLLM:
        async def execute(self, *_args, **_kwargs):
            raise AssertionError("LLM fallback must not run when a registered agent matches")

    monkeypatch.setattr(agent_router, "_get_self_model", lambda: FakeModel())
    monkeypatch.setattr(agent_router, "_get_llm", lambda: ForbiddenLLM())

    response = await agent_router.AgentRouter().route(
        IntentResult(intent=Intent.CONVERSATION, confidence="low"),
        "Combien de temps reste-t-il avant la WWDC ?",
    )

    assert "Temps restant avant la WWDC" in response


@pytest.mark.asyncio
async def test_registered_agent_is_reused_without_reconstruction(monkeypatch, tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    generated_agents = tmp_path / "core" / "agents" / "generated"
    generated_agents.mkdir(parents=True)
    orchestrator = AgentBuildOrchestrator(
        project_manager=manager,
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=generated_agents,
        runtime_check=False,
    )
    spec = orchestrator.plan_spec(
        "Créer un agent qui me donne le temps restant avant la prochaine WWDC d’Apple"
    )
    registered_agent = generated_agents / "event_countdown_agent.py"
    registered_agent.write_text(
        f"AGENT_SPEC = {json.dumps(spec.to_dict(), sort_keys=True)}\n"
        f"AGENT_SPEC_SIGNATURE = {orchestrator._spec_signature(spec)!r}\n"
        "class Agent:\n"
        "    name = 'event_countdown_agent'\n"
        "    async def execute(self, text=''):\n"
        "        return {'status': 'ok', 'response': 'available'}\n",
        encoding="utf-8",
    )
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(orchestrator, "_write_agent", lambda *_args, **_kwargs: pytest.fail("agent rewritten"))
    monkeypatch.setattr(orchestrator, "_write_agent_test", lambda *_args, **_kwargs: pytest.fail("test rewritten"))
    monkeypatch.setattr(orchestrator, "_register_agent", lambda *_args, **_kwargs: pytest.fail("agent re-registered"))
    monkeypatch.setattr(event_bus, "publish", fake_publish)

    result = await orchestrator.build_from_request(
        "Créer un agent qui me donne le temps restant avant la prochaine WWDC d’Apple"
    )

    assert result["status"] == "completed"
    assert result["reused_registered_agent"] is True
    assert result["reused_existing_agent"] is True
    assert result["build_executed"] is False
    assert result["reused_existing_project"] is False
    assert result["project"] is None
    assert result["agent"]["agent_name"] == "event_countdown_agent"
    assert result["agent"]["path"] == str(registered_agent)
    assert manager.list_projects(limit=10) == []
    assert "Agent déjà disponible : event_countdown_agent" in result["response"]
    assert "Tests déjà validés : OK" in result["response"]
    assert "Aucune reconstruction nécessaire" in result["response"]
    assert "Agent créé" not in result["response"]
    assert [event.type for event in published] == [event_types.AGENT_CONSULTED]
    assert published[0].payload["agent"] == "event_countdown_agent"


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


@pytest.mark.asyncio
async def test_build_orchestrator_preserves_agriculture_weather_specialization(tmp_path: Path):
    manager = ProjectManager(tmp_path / "projects.json")
    orchestrator = AgentBuildOrchestrator(
        project_manager=manager,
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
    )

    spec = orchestrator.plan_spec("Créer un agent météo spécialisé agriculture")
    assert spec.name == "agriculture_weather_agent"
    assert spec.goal == "Surveiller et repondre aux demandes meteo agricoles"
    assert spec.capabilities == [
        "parse_agriculture_weather_request",
        "static_agriculture_weather_fallback",
        "format_agriculture_weather_response",
    ]

    result = await orchestrator.build_from_request("Créer un agent météo spécialisé agriculture")

    project = result["project"]
    assert result["status"] == "completed"
    assert result["spec"]["name"] == "agriculture_weather_agent"
    assert project["registered_agent"] == "agriculture_weather_agent"
    assert project["registry_status"] == "registered"
    assert project["result"]["runtime_reload"]["ok"] is True
    assert "agriculture_weather_agent" in project["result"]["runtime_reload"]["agents"]
    generated = tmp_path / "core" / "agents" / "generated" / "agriculture_weather_agent.py"
    assert generated.exists()
    content = generated.read_text(encoding="utf-8")
    assert "parse_agriculture_weather_request" in content
    assert "Spécialisation agriculture" in content


@pytest.mark.asyncio
async def test_agent_build_refuses_sensitive_system_request(tmp_path: Path):
    orchestrator = AgentBuildOrchestrator(
        project_manager=ProjectManager(tmp_path / "projects.json"),
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
    )

    result = await orchestrator.build_from_request(
        "Créer un agent qui modifie les services système et lit les secrets"
    )

    assert result["status"] == "refused"
    assert result["build_executed"] is False
    assert result["safety"]["auto_apply_allowed"] is False
    assert not (tmp_path / "workspace" / "agents").exists()
    assert not (tmp_path / "core" / "agents" / "generated").exists()


@pytest.mark.asyncio
async def test_simple_weather_agent_still_builds_and_registers(tmp_path: Path):
    result = await AgentBuildOrchestrator(
        project_manager=ProjectManager(tmp_path / "projects.json"),
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
    ).build_from_request("Créer un agent météo")

    assert result["status"] == "completed"
    assert result["spec"]["name"] == "weather_watch_agent"
    assert result["project"]["registered_agent"] == "weather_watch_agent"
    assert result["project"]["registry_status"] == "registered"
    assert (tmp_path / "core" / "agents" / "generated" / "weather_watch_agent.py").exists()


@pytest.mark.asyncio
async def test_agent_build_deterministic_mode_does_not_call_codex(tmp_path: Path):
    class ForbiddenCodexRunner:
        async def run_codex(self, *_args, **_kwargs):
            raise AssertionError("deterministic mode must not call Codex")

    result = await AgentBuildOrchestrator(
        project_manager=ProjectManager(tmp_path / "projects.json"),
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
        codex_runner=ForbiddenCodexRunner(),
    ).build_from_request("Créer un agent nommé deterministic_phase_agent")

    assert result["status"] == "completed"
    assert result["build_mode"] == "deterministic"
    assert result["codex_used"] is False
    assert result["codex_ok"] is None
    assert result["codex_fallback"] is False
    assert result["project"]["registered_agent"] == "deterministic_phase_agent"


@pytest.mark.asyncio
async def test_agent_build_hybrid_calls_codex_and_promotes_workspace_output(tmp_path: Path):
    runner = FakeAgentBuilderCodexRunner(project_root=tmp_path)
    result = await AgentBuildOrchestrator(
        project_manager=ProjectManager(tmp_path / "projects.json"),
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
        codex_runner=runner,
    ).build_from_request("Créer un agent nommé hybrid_codex_agent", build_mode="hybrid")

    assert result["status"] == "completed"
    assert result["build_mode"] == "hybrid"
    assert result["codex_used"] is True
    assert result["codex_ok"] is True
    assert result["codex_fallback"] is False
    assert len(runner.calls) == 1
    assert "workspace/agents/hybrid_codex_agent.py" in runner.calls[0][0]
    assert "workspace/agent_tests/test_hybrid_codex_agent.py" in runner.calls[0][0]
    assert result["project"]["registered_agent"] == "hybrid_codex_agent"


@pytest.mark.asyncio
async def test_agent_build_hybrid_falls_back_to_deterministic_when_codex_fails(tmp_path: Path):
    runner = FakeAgentBuilderCodexRunner(returncode=1, project_root=tmp_path)
    result = await AgentBuildOrchestrator(
        project_manager=ProjectManager(tmp_path / "projects.json"),
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
        codex_runner=runner,
    ).build_from_request("Créer un agent nommé hybrid_fallback_agent", build_mode="hybrid")

    assert result["status"] == "completed"
    assert result["build_mode"] == "hybrid"
    assert result["codex_used"] is True
    assert result["codex_ok"] is False
    assert result["codex_fallback"] is True
    assert "codex failed" in result["codex_error"]
    assert result["project"]["registered_agent"] == "hybrid_fallback_agent"
    assert (tmp_path / "core" / "agents" / "generated" / "hybrid_fallback_agent.py").exists()


@pytest.mark.asyncio
async def test_agent_build_codex_mode_fails_cleanly_when_codex_fails(tmp_path: Path):
    runner = FakeAgentBuilderCodexRunner(returncode=1, project_root=tmp_path)
    result = await AgentBuildOrchestrator(
        project_manager=ProjectManager(tmp_path / "projects.json"),
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
        codex_runner=runner,
    ).build_from_request("Créer un agent nommé codex_failure_agent", build_mode="codex")

    assert result["status"] == "failed"
    assert result["build_mode"] == "codex"
    assert result["codex_used"] is True
    assert result["codex_ok"] is False
    assert result["codex_fallback"] is False
    assert result["project"]["current_step"] == "codex"
    assert result["project"]["registry_status"] == "not_registered"
    assert not (tmp_path / "core" / "agents" / "generated" / "codex_failure_agent.py").exists()


@pytest.mark.asyncio
async def test_agent_build_blocks_direct_codex_write_to_generated_dir(tmp_path: Path):
    generated = tmp_path / "core" / "agents" / "generated"
    runner = FakeAgentBuilderCodexRunner(generated_dir=generated, project_root=tmp_path)
    result = await AgentBuildOrchestrator(
        project_manager=ProjectManager(tmp_path / "projects.json"),
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=generated,
        runtime_check=False,
        codex_runner=runner,
    ).build_from_request("Créer un agent nommé generated_guard_agent", build_mode="hybrid")

    assert result["status"] == "completed"
    assert result["codex_ok"] is False
    assert result["codex_fallback"] is True
    assert result["codex_error"] == "codex_generated_dir_write_blocked"
    assert not (generated / "codex_direct_write_agent.py").exists()
    assert (generated / "generated_guard_agent.py").exists()


@pytest.mark.asyncio
async def test_telegram_route_equivalent_builds_agriculture_agent_without_approval(monkeypatch, tmp_path: Path):
    orchestrator = AgentBuildOrchestrator(
        project_manager=ProjectManager(tmp_path / "projects.json"),
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
    )

    monkeypatch.setattr(build_orchestrator, "AgentBuildOrchestrator", lambda: orchestrator)

    response = await agent_router._build_tracked_agent(
        "Créer un agent météo spécialisé agriculture",
        source_channel="telegram",
    )

    assert "Projet terminé" in response
    assert "Agent créé : agriculture_weather_agent" in response
    assert "Tests : OK" in response
    assert "Agent enregistré : oui" in response
    assert "Runtime rechargé : OK" in response
    project = ProjectManager(tmp_path / "projects.json").list_projects(limit=1)[0]
    assert project["source_channel"] == "telegram"
    assert project["registered_agent"] == "agriculture_weather_agent"


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
    calls: list[tuple[str, str, str, str]] = []

    class FakeModel:
        def set_last_intent(self, *_args):
            return None

        def add_recent_activity(self, *_args):
            return None

    class FakeOrchestrator:
        async def build_from_request(
            self,
            query: str,
            *,
            requested_by: str,
            source_channel: str,
            build_mode: str = "deterministic",
        ):
            calls.append((query, requested_by, source_channel, build_mode))
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
    assert calls == [("Créer un agent de test", "user", "api", "hybrid")]


@pytest.mark.asyncio
async def test_agent_router_default_creation_path_uses_hybrid_build_mode(monkeypatch):
    calls: list[tuple[str, str, str, str]] = []

    class FakeModel:
        def set_last_intent(self, *_args):
            return None

        def add_recent_activity(self, *_args):
            return None

    class FakeOrchestrator:
        async def build_from_request(
            self,
            query: str,
            *,
            requested_by: str,
            source_channel: str,
            build_mode: str = "deterministic",
        ):
            calls.append((query, requested_by, source_channel, build_mode))
            return {"status": "completed", "response": "orchestrated"}

        def format_project_response(self, project):
            return "formatted"

    monkeypatch.setattr(agent_router, "_get_self_model", lambda: FakeModel())
    monkeypatch.setattr(build_orchestrator, "AgentBuildOrchestrator", FakeOrchestrator)

    result = await agent_router.AgentRouter().route(
        IntentResult(intent=Intent.AGENT_CREATION, confidence="high"),
        "Créer un agent nommé eclipse_telegram_codex_agent qui surveille les éclipses",
    )

    assert result == "orchestrated"
    assert calls == [
        (
            "Créer un agent nommé eclipse_telegram_codex_agent qui surveille les éclipses",
            "user",
            "api",
            "hybrid",
        )
    ]


@pytest.mark.asyncio
async def test_telegram_goal_agent_creation_uses_hybrid_build_mode():
    from core.goals.goal_orchestrator import GoalOrchestrator

    calls: list[tuple[str, str, str, str]] = []

    class FakeStorage:
        def update(self, plan):
            self.plan = dict(plan)

    class FakeTaskManager:
        def __init__(self):
            self.tasks: list[dict] = []

        def create_tasks_from_plan(self, plan):
            self.tasks = [
                {
                    "id": "task-1",
                    "plan_id": plan["id"],
                    "title": "Créer agent",
                    "action": "create_skeleton",
                    "agent": "agent_creator",
                    "status": "active",
                }
            ]
            return self.tasks

        def list_tasks(self):
            return self.tasks

        def update_task(self, task_id, updates):
            task = next(item for item in self.tasks if item["id"] == task_id)
            task.update(updates)
            return task

        def _now(self):
            return "2026-06-04T00:00:00+00:00"

    class FakeGoalManager:
        def update_progress(self, *_args):
            return None

        def update_status(self, *_args):
            return None

    class FakeBuildOrchestrator:
        async def build_from_request(
            self,
            query: str,
            *,
            requested_by: str,
            source_channel: str,
            build_mode: str = "deterministic",
        ):
            calls.append((query, requested_by, source_channel, build_mode))
            return {
                "status": "completed",
                "build_mode": build_mode,
                "codex_used": True,
                "codex_ok": True,
                "codex_fallback": False,
                "project": {
                    "project_id": "agent_eclipse",
                    "registered_agent": "eclipse_telegram_codex_agent",
                    "registry_status": "registered",
                    "created_files": [
                        "workspace/agents/eclipse_telegram_codex_agent.py",
                        "workspace/agent_tests/test_eclipse_telegram_codex_agent.py",
                        "core/agents/generated/eclipse_telegram_codex_agent.py",
                    ],
                    "test_results": [{"returncode": 0}],
                    "result": {
                        "agent": "eclipse_telegram_codex_agent",
                        "available": True,
                        "runtime_reload": {"ok": True, "agents": ["eclipse_telegram_codex_agent"]},
                    },
                },
                "spec": {
                    "name": "eclipse_telegram_codex_agent",
                    "goal": "Créer un agent nommé eclipse_telegram_codex_agent",
                    "capabilities": ["deterministic_response"],
                },
            }

    async def notifier(*_args):
        return None

    orchestrator = GoalOrchestrator.__new__(GoalOrchestrator)
    orchestrator.storage = FakeStorage()
    orchestrator.task_manager = FakeTaskManager()
    orchestrator.goal_manager = FakeGoalManager()
    orchestrator.agent_build_orchestrator = FakeBuildOrchestrator()
    orchestrator.notifier = notifier

    plan = {
        "id": "plan-telegram",
        "goal_id": "goal-telegram",
        "goal": "Créer un agent nommé eclipse_telegram_codex_agent",
        "source": "telegram_goal",
        "approved": True,
        "steps": [{"agent": "agent_creator", "action": "create_skeleton"}],
    }

    result = await orchestrator.execute_agent_build_plan(plan, approved_by="risk_policy")

    assert result["status"] == "plan_finished"
    assert calls == [
        (
            "Créer un agent nommé eclipse_telegram_codex_agent",
            "risk_policy",
            "telegram",
            "hybrid",
        )
    ]
    assert result["plan"]["build_mode"] == "hybrid"
    assert result["plan"]["codex_used"] is True
    assert result["plan"]["codex_fallback"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["liste agents", "affiche les agents"])
async def test_agent_list_variants_use_same_registry_action(monkeypatch, query):
    class FakeModel:
        def set_last_intent(self, *_args):
            return None

        def add_recent_activity(self, *_args):
            return None

    calls: list[str] = []

    def fake_list_dynamic_agents() -> str:
        calls.append("list")
        return "Agents dynamiques disponibles :\n- demo_agent"

    monkeypatch.setattr(agent_router, "_get_self_model", lambda: FakeModel())
    monkeypatch.setattr(agent_router, "_list_dynamic_agents", fake_list_dynamic_agents)

    response = await agent_router.AgentRouter().route(
        IntentResult(intent=Intent.CONVERSATION, confidence="low"),
        query,
    )

    assert response == "Agents dynamiques disponibles :\n- demo_agent"
    assert calls == ["list"]


@pytest.mark.asyncio
async def test_agent_registry_telegram_commands_use_scanner(monkeypatch):
    from core.agent_factory import registry_scanner

    class FakeModel:
        def set_last_intent(self, *_args):
            return None

        def add_recent_activity(self, *_args):
            return None

    calls: list[str] = []

    class FakeScanner:
        async def scan(self):
            calls.append("scan")
            return {
                "status": "ok",
                "scanned": 2,
                "active": 1,
                "invalid": 1,
                "runtime_reloaded": True,
            }

        def get_index(self):
            calls.append("index")
            return {
                "agents": {
                    "active_scan_agent": {
                        "agent_name": "active_scan_agent",
                        "status": "active",
                        "source": "generated_scan",
                    },
                    "invalid_scan_agent": {
                        "agent_name": "invalid_scan_agent",
                        "status": "invalid",
                        "error": "méthode async execute manquante",
                        "source": "generated_scan",
                    },
                }
            }

    monkeypatch.setattr(agent_router, "_get_self_model", lambda: FakeModel())
    monkeypatch.setattr(registry_scanner, "AgentRegistryScanner", FakeScanner)

    scan_response = await agent_router.AgentRouter().route(
        IntentResult(intent=Intent.CONVERSATION, confidence="low"),
        "rescanner agents",
    )
    invalid_response = await agent_router.AgentRouter().route(
        IntentResult(intent=Intent.CONVERSATION, confidence="low"),
        "agents invalides",
    )
    index_response = await agent_router.AgentRouter().route(
        IntentResult(intent=Intent.CONVERSATION, confidence="low"),
        "index agents",
    )

    assert "Scan agents terminé." in scan_response
    assert "Agents scannés : 2." in scan_response
    assert "Runtime rechargé : OK." in scan_response
    assert "invalid_scan_agent" in invalid_response
    assert "méthode async execute manquante" in invalid_response
    assert "- active_scan_agent | active" in index_response
    assert "- invalid_scan_agent | invalid" in index_response
    assert calls == ["scan", "index", "index"]


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


@pytest.mark.asyncio
async def test_agent_build_route_defaults_to_deterministic(monkeypatch):
    from core.projects import routes

    calls: list[tuple[str, str, str, str]] = []

    class FakeOrchestrator:
        async def build_from_request(
            self,
            query: str,
            *,
            requested_by: str,
            source_channel: str,
            build_mode: str = "deterministic",
        ):
            calls.append((query, requested_by, source_channel, build_mode))
            return {"status": "completed"}

    monkeypatch.setattr(routes, "AgentBuildOrchestrator", FakeOrchestrator)

    result = await routes.build_agent(routes.AgentBuildRequest(query="Créer un agent nommé api_default_agent"))

    assert result["status"] == "completed"
    assert calls == [("Créer un agent nommé api_default_agent", "api", "api", "deterministic")]


@pytest.mark.asyncio
async def test_agent_manager_routes_expose_status_inspect_delete(monkeypatch):
    from core.projects import routes

    calls: list[tuple[str, str]] = []

    class FakeManager:
        def get_agent_status(self, agent_name: str):
            calls.append(("status", agent_name))
            return {"status": "ok", "agent": agent_name}

        def inspect_agent(self, agent_name: str):
            calls.append(("inspect", agent_name))
            return {"status": "ok", "agent": agent_name, "source_preview": "class Agent"}

        def delete_agent(self, agent_name: str):
            calls.append(("delete", agent_name))
            return {"status": "deleted", "agent": agent_name, "backup": {"backup_created": True}}

    monkeypatch.setattr(routes, "AgentManager", FakeManager)

    status = await routes.agent_status("managed_route_agent")
    inspection = await routes.inspect_agent("managed_route_agent")
    deletion = await routes.delete_agent("managed_route_agent")

    assert status["status"] == "ok"
    assert inspection["source_preview"] == "class Agent"
    assert deletion["backup"]["backup_created"] is True
    assert calls == [
        ("status", "managed_route_agent"),
        ("inspect", "managed_route_agent"),
        ("delete", "managed_route_agent"),
    ]


@pytest.mark.asyncio
async def test_agent_registry_scanner_routes_expose_scan_and_index(monkeypatch):
    from core.projects import routes

    calls: list[str] = []

    class FakeScanner:
        async def scan(self):
            calls.append("scan")
            return {"status": "ok", "scanned": 1, "runtime_reloaded": True}

        def get_index(self):
            calls.append("index")
            return {
                "agents": {
                    "route_scan_agent": {
                        "agent_name": "route_scan_agent",
                        "status": "active",
                        "source": "generated_scan",
                    }
                }
            }

    monkeypatch.setattr(routes, "AgentRegistryScanner", FakeScanner)

    scan_get = await routes.scan_agent_registry_get()
    scan_post = await routes.scan_agent_registry_post()
    index = await routes.agent_registry_index()

    assert scan_get["status"] == "ok"
    assert scan_post["runtime_reloaded"] is True
    assert index["agents"]["route_scan_agent"]["source"] == "generated_scan"
    assert calls == ["scan", "scan", "index"]


@pytest.mark.asyncio
async def test_project_route_exposes_failure_diagnostics(monkeypatch, tmp_path: Path):
    from core.projects import routes

    manager = ProjectManager(tmp_path / "projects.json")
    project = manager.create_project(
        title="Evolution Codex",
        project_type="evolution",
        requested_by="test",
        source_channel="api",
        query="Faire évoluer Néron",
    )
    manager.update_project(project["project_id"], {"status": "running"}, step="codex_running")
    manager.update_project(
        project["project_id"],
        {"status": "failed", "current_step": "failed"},
        step="failed",
        step_status="failed",
        error="Codex a échoué.",
    )
    monkeypatch.setattr(routes, "get_project_manager", lambda: manager)

    diagnostics = await routes.diagnose_project_failures(limit=5)

    assert diagnostics["count"] == 1
    assert diagnostics["projects"][0]["project_id"] == project["project_id"]
    assert diagnostics["projects"][0]["category"] == "codex_execution_failed"
    assert diagnostics["projects"][0]["retry_requires_validation"] is True
