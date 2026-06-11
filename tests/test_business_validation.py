from __future__ import annotations

from pathlib import Path

import pytest

from core.agent_factory.build_orchestrator import AgentBuildOrchestrator
from core.goals.execution_engine import GoalExecutionEngine
from core.projects.manager import ProjectManager
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


def write_agent(path: Path, response: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "class Agent:",
                "    async def execute(self, text=''):",
                "        return {",
                "            'status': 'ok',",
                f"            'response': {response!r},",
                "        }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def make_builder(tmp_path: Path) -> AgentBuildOrchestrator:
    return AgentBuildOrchestrator(
        project_manager=ProjectManager(tmp_path / "data" / "projects.json"),
        project_root=tmp_path,
        workspace_agents=tmp_path / "workspace" / "agents",
        workspace_tests=tmp_path / "workspace" / "agent_tests",
        generated_agents=tmp_path / "core" / "agents" / "generated",
        runtime_check=False,
        runtime_governor=AllowGovernor(),
    )


def test_easter_2027_business_validation_passes(tmp_path: Path):
    agent_file = write_agent(
        tmp_path / "easter_agent.py",
        "Pâques tombe le 28 mars 2027.",
    )
    validator = BusinessValidator(project_root=tmp_path)

    result = validator.validate(
        {"name": "easter_agent", "goal": "Donner la date de Pâques"},
        agent_file,
        "Créer un agent qui donne la date de Pâques",
    )

    assert result["ok"] is True
    assert result["status"] == "passed"
    assert result["scenario"]["name"] == "easter_2027"
    assert result["actual_response"] == "Pâques tombe le 28 mars 2027."
    assert result["errors"] == []


def test_easter_generic_response_fails_business_validation(tmp_path: Path):
    agent_file = write_agent(
        tmp_path / "easter_agent.py",
        "Agent disponible pour : Créer un agent qui donne la date de Pâques",
    )
    validator = BusinessValidator(project_root=tmp_path)

    result = validator.validate(
        {"name": "easter_agent", "goal": "Donner la date de Pâques"},
        agent_file,
        "Créer un agent qui donne la date de Pâques",
    )

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert result["expected"]["contains_all"] == ["2027"]
    assert result["errors"]


@pytest.mark.parametrize(
    ("goal", "response", "scenario_name"),
    [
        (
            "Créer un agent qui donne le temps restant avant Noël",
            "Il reste 198 jours avant Noël, le 25/12.",
            "christmas_countdown",
        ),
        (
            "Créer un agent qui calcule un subnet IPv4",
            "Réseau: 192.168.1.0/24",
            "ipv4_subnet",
        ),
    ],
)
def test_supported_business_scenarios_pass(
    tmp_path: Path,
    goal: str,
    response: str,
    scenario_name: str,
):
    agent_file = write_agent(tmp_path / f"{scenario_name}.py", response)

    result = BusinessValidator(project_root=tmp_path).validate(
        {"name": scenario_name, "goal": goal},
        agent_file,
        goal,
    )

    assert result["ok"] is True
    assert result["scenario"]["name"] == scenario_name


@pytest.mark.parametrize(
    "response",
    [
        "Agent disponible pour : une demande simple",
        "Je suis un agent de démonstration",
        "Réponse déterministe",
    ],
)
def test_generic_fallback_rejects_non_business_claims(
    tmp_path: Path,
    response: str,
):
    agent_file = write_agent(tmp_path / "generic_agent.py", response)

    result = BusinessValidator(project_root=tmp_path).validate(
        {"name": "generic_agent", "goal": "Traiter une demande simple"},
        agent_file,
        "Créer un agent nommé generic_agent",
    )

    assert result["ok"] is False
    assert any("generic_response_rejected" in error for error in result["errors"])


def test_internal_capability_without_reliable_scenario_fails(tmp_path: Path):
    agent_file = write_agent(
        tmp_path / "generic_internal_agent.py",
        "Réponse métier apparemment utile.",
    )

    result = BusinessValidator(project_root=tmp_path).validate(
        {
            "name": "generic_internal_agent",
            "goal": "Traiter une capacité inconnue",
        },
        agent_file,
        "Créer une capacité inconnue",
        context={
            "internal_capability_request": True,
            "creation_type": "tool",
            "capability_request_id": "cap-unknown",
        },
    )

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert result["scenario"]["name"] == "unsupported_internal_capability"
    assert result["scenario"]["fallback"] is False
    assert result["errors"] == ["reliable_business_scenario_required"]


def test_internal_log_capability_rejects_generic_response(tmp_path: Path):
    agent_file = write_agent(
        tmp_path / "generic_log_agent.py",
        "Demande traitée : Analyse les logs Néron",
    )

    result = BusinessValidator(project_root=tmp_path).validate(
        {
            "name": "generic_log_agent",
            "goal": "Analyser automatiquement les logs Néron",
        },
        agent_file,
        "Analyse automatiquement les logs Néron et résume les erreurs critiques",
        context={
            "internal_capability_request": True,
            "creation_type": "agent",
            "capability_request_id": "cap-logs-generic",
        },
    )

    assert result["ok"] is False
    assert result["scenario"]["name"] == "neron_log_analysis"
    assert any("generic_response_rejected" in error for error in result["errors"])


def test_internal_log_capability_accepts_specialized_response(tmp_path: Path):
    agent_file = write_agent(
        tmp_path / "specialized_log_agent.py",
        "Analyse des logs Néron terminée : aucune erreur critique détectée.",
    )

    result = BusinessValidator(project_root=tmp_path).validate(
        {
            "name": "specialized_log_agent",
            "goal": "Analyser automatiquement les logs Néron",
        },
        agent_file,
        "Analyse automatiquement les logs Néron et résume les erreurs critiques",
        context={
            "internal_capability_request": True,
            "creation_type": "agent",
            "capability_request_id": "cap-logs-specialized",
        },
    )

    assert result["ok"] is True
    assert result["status"] == "passed"
    assert result["scenario"]["name"] == "neron_log_analysis"
    assert result["scenario"]["fallback"] is False


@pytest.mark.asyncio
async def test_business_failure_after_pytest_is_not_registered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    builder = make_builder(tmp_path)
    engine = GoalExecutionEngine(builder.project_manager.sqlite_store)
    engine.enqueue_goal("goal-business-failure", "Validation métier", "test", {})
    engine.start_goal("goal-business-failure")

    def write_incorrect_easter_agent(spec):
        return write_agent(
            builder.workspace_agents / f"{spec.name}.py",
            "Agent disponible pour : Créer un agent qui donne la date de Pâques",
        )

    monkeypatch.setattr(builder, "_write_agent", write_incorrect_easter_agent)

    result = await builder.build_from_request(
        "Créer un agent qui donne la date de Pâques",
        tracking_context={"goal_id": "goal-business-failure"},
    )

    project = result["project"]
    assert result["status"] == "failed"
    assert project["compile_status"] == "passed"
    assert project["test_status"] == "passed"
    assert project["business_validation_status"] == "failed"
    assert project["current_step"] == "business_validation"
    assert project["registry_status"] == "not_registered"
    assert project["error"]
    run = engine.get_goal_status("goal-business-failure")
    assert run["status"] == "failed"
    assert run["current_step"] == "business_validation"
    assert any(
        event["step"] == "business_validation"
        and event["status"] == "failed"
        for event in engine.get_goal_events("goal-business-failure")
    )
    assert not (
        tmp_path / "core" / "agents" / "generated" / "donne_la_date_agent.py"
    ).exists()


@pytest.mark.asyncio
async def test_internal_generic_log_build_is_not_registered_or_available(
    tmp_path: Path,
):
    builder = make_builder(tmp_path)

    result = await builder.build_from_request(
        "Créer un agent durable qui répond à cette demande : "
        "Analyse automatiquement les logs Néron et résume les erreurs critiques",
        tracking_context={
            "internal_capability_request": True,
            "creation_type": "agent",
            "capability_request_id": "cap-log-build",
        },
    )

    project = result["project"]
    assert result["status"] == "failed"
    assert project["current_step"] == "business_validation"
    assert project["business_validation_status"] == "failed"
    assert project["registry_status"] == "not_registered"
    assert project["runtime_status"] == "not_available"
    assert project["result"]["available"] is False
    assert not list((tmp_path / "core" / "agents" / "generated").glob("*.py"))


@pytest.mark.asyncio
async def test_deterministic_easter_2027_is_validated_and_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    builder = make_builder(tmp_path)

    async def successful_verification(spec):
        return {
            "ok": True,
            "response": "Pâques 2027 tombe le 28 mars 2027.",
            "runtime_reload": {"ok": True, "agents": [spec.name]},
        }

    monkeypatch.setattr(builder, "_verify_agent", successful_verification)

    result = await builder.build_from_request(
        "Créer un agent nommé easter_2027_agent qui donne la date exacte de Pâques 2027"
    )

    project = result["project"]
    response = project["business_validation_result"]["actual_response"]
    assert result["status"] == "completed"
    assert "2027" in response
    assert "28 mars" in response or "2027-03-28" in response
    assert project["business_validation_status"] == "passed"
    assert project["registry_status"] == "registered"
    assert project["runtime_status"] == "available"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("goal", "expected_value"),
    [
        (
            "Créer un agent nommé christmas_2028_agent pour donner la date de Noël 2028",
            "25/12/2028",
        ),
        (
            "Créer un agent nommé ipv4_subnet_agent qui calcule un subnet IPv4",
            "192.168.1.0",
        ),
    ],
)
async def test_deterministic_known_business_agents_pass_validation(
    tmp_path: Path,
    goal: str,
    expected_value: str,
):
    result = await make_builder(tmp_path).build_from_request(goal)

    project = result["project"]
    assert result["status"] == "completed"
    assert project["business_validation_status"] == "passed"
    assert expected_value in project["business_validation_result"]["actual_response"]
    assert project["registry_status"] == "registered"


@pytest.mark.asyncio
async def test_generic_agents_without_reliable_scenario_remain_compatible(
    tmp_path: Path,
):
    builder = make_builder(tmp_path)

    result = await builder.build_from_request(
        "Créer un agent nommé legacy_simple_agent"
    )

    project = result["project"]
    assert result["status"] == "completed"
    assert project["business_validation_status"] == "passed"
    assert project["business_validation_result"]["scenario"]["fallback"] is True
    assert project["registry_status"] == "registered"
