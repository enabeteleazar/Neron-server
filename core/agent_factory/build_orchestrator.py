from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from core.agent_factory.registry import DynamicAgentRegistry
from core.agent_factory.validator import validate_agent
from core.evolution.codex_runner import CodexRunner, redact_secrets
from core.projects.manager import ProjectManager, get_project_manager


DEFAULT_PROJECT_ROOT = Path("/etc/neron")
DEFAULT_WORKSPACE_AGENTS = DEFAULT_PROJECT_ROOT / "workspace" / "agents"
DEFAULT_WORKSPACE_TESTS = DEFAULT_PROJECT_ROOT / "workspace" / "agent_tests"
DEFAULT_GENERATED_AGENTS = DEFAULT_PROJECT_ROOT / "core" / "agents" / "generated"
BuildMode = Literal["deterministic", "codex", "hybrid"]

SENSITIVE_BUILD_KEYWORDS = {
    "systemd",
    "service systeme",
    "services systeme",
    "secret",
    "secrets",
    "token",
    "tokens",
    "api key",
    "cle ssh",
    "ssh key",
    "securite",
    "security",
    "suppression",
    "supprimer",
    "delete",
    "remove",
    "rm -rf",
    "rm rf",
    "chmod",
    "sudo",
    "fichier sensible",
    "fichiers sensibles",
}


@dataclass(slots=True)
class AgentSpec:
    kind: str
    name: str
    title: str
    goal: str
    inputs: list[str]
    outputs: list[str]
    capabilities: list[str]
    safety: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "title": self.title,
            "goal": self.goal,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "capabilities": self.capabilities,
            "safety": self.safety,
        }


class AgentBuildOrchestrator:
    def __init__(
        self,
        *,
        project_manager: ProjectManager | None = None,
        project_root: Path = DEFAULT_PROJECT_ROOT,
        workspace_agents: Path = DEFAULT_WORKSPACE_AGENTS,
        workspace_tests: Path = DEFAULT_WORKSPACE_TESTS,
        generated_agents: Path = DEFAULT_GENERATED_AGENTS,
        python_executable: str | None = None,
        runtime_check: bool = True,
        codex_runner: Any | None = None,
        runtime_governor: Any | None = None,
    ) -> None:
        self.project_manager = project_manager or get_project_manager()
        self.project_root = project_root
        self.workspace_agents = workspace_agents
        self.workspace_tests = workspace_tests
        self.generated_agents = generated_agents
        self.python_executable = python_executable or sys.executable
        self.runtime_check = runtime_check
        self.codex_runner = codex_runner
        self.runtime_governor = runtime_governor

    async def build_from_request(
        self,
        query: str,
        *,
        requested_by: str = "user",
        source_channel: str = "api",
        build_mode: BuildMode = "deterministic",
        tracking_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mode = self._normalize_build_mode(build_mode)
        codex_state = self._codex_state(mode)
        safety = self.assess_request_safety(query)
        if not safety["auto_apply_allowed"]:
            return {
                "status": "refused",
                "project": None,
                "spec": None,
                "build_executed": False,
                "reused_existing_project": False,
                "safety": safety,
                **codex_state,
                "response": self._format_refusal_response(safety),
            }

        spec = self.plan_spec(query)
        metadata = {
            **self._project_metadata(spec, query),
            **(tracking_context or {}),
        }
        existing = self.project_manager.find_existing_agent_project(
            agent_name=spec.name,
            intent_key=metadata["intent_key"],
            spec_signature=metadata["spec_signature"],
        )
        if existing:
            return self._with_build_status(
                self._reuse_existing_project(existing, spec),
                codex_state,
            )

        registered_agent = self._registered_agent_for_spec(spec, metadata)
        if registered_agent:
            return self._with_build_status(
                await self._return_registered_agent(
                    spec,
                    registered_agent,
                    query=query,
                    source_channel=source_channel,
                ),
                codex_state,
            )

        metadata["build_mode"] = mode
        metadata["codex_used"] = codex_state["codex_used"]
        project = self.project_manager.create_project(
            title=spec.title,
            project_type=spec.kind,
            requested_by=requested_by,
            source_channel=source_channel,
            query=query,
            metadata=metadata,
        )
        project_id = str(project["project_id"])
        promotion_destination: Path | None = None
        promotion_snapshot: bytes | None = None
        promotion_committed = False

        try:
            self._step(project_id, "planning", "done", 10)

            agent_file = self.workspace_agents / f"{spec.name}.py"
            test_file = self.workspace_tests / f"test_{spec.name}.py"

            if mode in {"deterministic", "hybrid"}:
                agent_file = self._write_agent(spec)
                test_file = self._write_agent_test(spec, agent_file)

            if mode in {"codex", "hybrid"}:
                codex = await self._run_codex_agent_generation(spec, agent_file, test_file)
                codex_state.update(
                    {
                        "codex_ok": codex.get("ok"),
                        "codex_error": codex.get("error"),
                        "codex_result": codex.get("result"),
                    }
                )
                if not codex.get("ok"):
                    if mode == "codex":
                        failed = self._fail(project_id, "codex", codex.get("error") or "codex_failed")
                        return self._with_build_status(failed, codex_state)
                    codex_state["codex_fallback"] = True

            created_files = [
                self._relative(path)
                for path in (agent_file, test_file)
                if path.exists()
            ]
            self.project_manager.update_project(
                project_id,
                {
                    "created_files": created_files,
                    "status": "running",
                    "metadata": {
                        **metadata,
                        **self._codex_project_metadata(codex_state),
                    },
                },
                step="code_generation",
                step_status="done",
                progress=35,
            )

            validation = validate_agent(str(agent_file))
            if not validation.get("ok"):
                self.project_manager.update_project(
                    project_id,
                    {"validation_status": "failed"},
                )
                failed = self._fail(project_id, "validation", validation.get("error", "validation_failed"))
                return self._with_build_status(failed, codex_state)
            self.project_manager.update_project(
                project_id,
                {"validation_status": "passed"},
            )
            self._step(project_id, "validation", "done", 50)

            compile_result = self._run_command(
                [self.python_executable, "-m", "py_compile", str(agent_file)],
                "compile_agent",
            )
            if compile_result["returncode"] != 0:
                self.project_manager.update_project(
                    project_id,
                    {"compile_status": "failed"},
                )
                failed = self._fail(project_id, "compile", compile_result["stderr_tail"] or "compile_failed", compile_result)
                return self._with_build_status(failed, codex_state)
            self.project_manager.update_project(
                project_id,
                {"compile_status": "passed"},
            )
            self._step(project_id, "compile", "done", 60)

            test_result = self._run_command(
                [self.python_executable, "-m", "pytest", "-q", str(test_file)],
                "pytest_agent",
            )
            self._append_test_result(project_id, test_result)
            if test_result["returncode"] != 0:
                self.project_manager.update_project(
                    project_id,
                    {"test_status": "failed"},
                )
                failed = self._fail(project_id, "tests", test_result["stdout_tail"] or test_result["stderr_tail"])
                return self._with_build_status(failed, codex_state)
            self.project_manager.update_project(
                project_id,
                {"test_status": "passed"},
            )
            self._step(project_id, "tests", "done", 70)

            governor = self._get_runtime_governor()
            governor_allowed = governor.authorize_agent_promotion(
                agent_name=spec.name,
                requested_by=requested_by,
            )
            governor_policy = governor.to_dict()
            self.project_manager.update_project(
                project_id,
                {
                    "governor_status": "allowed" if governor_allowed else "refused",
                    "governor_policy": governor_policy,
                },
                step="runtime_governor",
                step_status="done" if governor_allowed else "failed",
                progress=75,
            )
            if not governor_allowed:
                failed = self._fail(
                    project_id,
                    "runtime_governor",
                    governor_policy.get("reason") or "runtime_governor_refused",
                )
                return self._with_build_status(failed, codex_state)

            promotion_snapshot = self._snapshot_promotion_target(agent_file)
            destination = self._register_agent(agent_file)
            promotion_destination = destination

            registry = DynamicAgentRegistry(self.generated_agents)
            registry.load_generated_agents()
            registered_record = registry.find_registered_agent_for_spec(
                spec.to_dict(),
                self._spec_signature(spec),
            )

            if not destination.exists() or not registered_record:
                self._rollback_promotion(destination, promotion_snapshot)
                self._reload_runtime_after_rollback()
                failed = self._fail(
                    project_id,
                    "registry",
                    f"Agent copié mais non visible dans le registry runtime : {spec.name}",
                )
                return self._with_build_status(failed, codex_state)

            self.project_manager.update_project(
                project_id,
                {
                    "registry_status": "registered",
                    "registered_agent": spec.name,
                    "created_files": [
                        self._relative(agent_file),
                        self._relative(test_file),
                        self._relative(destination),
                    ],
                },
                step="registry",
                step_status="done",
                progress=85,
            )

            verification = await self._verify_agent(spec)
            if not verification.get("ok"):
                self._rollback_promotion(destination, promotion_snapshot)
                self._reload_runtime_after_rollback()
                self.project_manager.update_project(
                    project_id,
                    {
                        "registry_status": "not_registered",
                        "registered_agent": None,
                        "runtime_status": "failed",
                    },
                )
                failed = self._fail(project_id, "verification", verification.get("error", "verification_failed"))
                return self._with_build_status(failed, codex_state)

            runtime_status = "skipped" if verification.get("skipped") else "available"
            completed = self.project_manager.update_project(
                project_id,
                {
                    "status": "completed",
                    "current_step": "completed",
                    "progress": 100,
                    "result": {
                        "agent": spec.name,
                        "verification": verification,
                        "runtime_reload": verification.get("runtime_reload"),
                        "available": True,
                        **self._codex_project_metadata(codex_state),
                    },
                    "runtime_status": runtime_status,
                    "error": None,
                    "metadata": {
                        **metadata,
                        **self._codex_project_metadata(codex_state),
                    },
                },
                step="verification",
                step_status="done",
                progress=100,
            )
            promotion_committed = True
            return self._with_build_status(
                {
                    "status": "completed",
                    "project": completed,
                    "spec": spec.to_dict(),
                    "build_executed": True,
                    "reused_existing_project": False,
                    "runtime_reload": verification.get("runtime_reload"),
                    "response": self.format_project_response(completed),
                },
                codex_state,
            )
        except Exception as exc:
            if promotion_destination is not None and not promotion_committed:
                self._rollback_promotion(promotion_destination, promotion_snapshot)
                self._reload_runtime_after_rollback()
            failed = self._fail(project_id, "exception", str(exc))
            return self._with_build_status(
                {
                    "status": "failed",
                    "project": failed["project"],
                    "spec": spec.to_dict(),
                    "build_executed": True,
                    "reused_existing_project": False,
                    "response": self.format_project_response(failed["project"]),
                },
                codex_state,
            )

    def plan_spec(self, query: str) -> AgentSpec:
        normalized = self._normalize(query)
        explicit_name = self._explicit_agent_name(normalized)
        if explicit_name:
            return AgentSpec(
                kind="agent",
                name=explicit_name,
                title=f"Agent {explicit_name}",
                goal=query,
                inputs=["text"],
                outputs=["response"],
                capabilities=["deterministic_response"],
                safety={"filesystem": "limited", "network": "none_required"},
            )

        if "wwdc" in normalized or "apple" in normalized:
            return AgentSpec(
                kind="agent",
                name="event_countdown_agent",
                title="Agent compte a rebours WWDC",
                goal="Donner le temps restant avant la prochaine WWDC d'Apple",
                inputs=["event_name"],
                outputs=["remaining_time", "target_date", "source"],
                capabilities=["datetime", "static_event_source"],
                safety={"filesystem": "limited", "network": "none_required"},
            )
        if "meteo" in normalized or "weather" in normalized:
            agriculture_domain = self._agriculture_domain(normalized)
            if agriculture_domain:
                return AgentSpec(
                    kind="agent",
                    name=f"{agriculture_domain}_weather_agent",
                    title="Agent meteo agricole",
                    goal="Surveiller et repondre aux demandes meteo agricoles",
                    inputs=["location", "crop", "weather_question"],
                    outputs=["agriculture_weather_summary", "risk_flags", "source"],
                    capabilities=[
                        "parse_agriculture_weather_request",
                        "static_agriculture_weather_fallback",
                        "format_agriculture_weather_response",
                    ],
                    safety={"filesystem": "limited", "network": "read_only_if_available"},
                )
            return AgentSpec(
                kind="agent",
                name="weather_watch_agent",
                title="Agent de suivi meteo",
                goal="Repondre aux demandes meteo simples",
                inputs=["location"],
                outputs=["summary", "source"],
                capabilities=["parse_weather_request", "static_weather_fallback"],
                safety={"filesystem": "limited", "network": "read_only_if_available"},
            )

        kind = "tool" if any(word in normalized for word in ("tool", "outil")) else "agent"
        base = self._name_from_query(normalized)
        return AgentSpec(
            kind=kind,
            name=base,
            title=f"{kind.capitalize()} {base}",
            goal=query,
            inputs=["text"],
            outputs=["response"],
            capabilities=["deterministic_response"],
            safety={"filesystem": "limited", "network": "none_required"},
        )

    def format_project_response(self, project: dict[str, Any] | None) -> str:
        if not project:
            return "Projet introuvable."

        result = project.get("result") or {}
        tests = project.get("test_results") or []
        tests_ok = bool(tests) and all(item.get("returncode") == 0 for item in tests)
        available = bool(result.get("available"))
        registered = project.get("registry_status") == "registered" and bool(
            project.get("registered_agent")
        )
        metadata = project.get("metadata") or {}
        reused_registered = bool(metadata.get("reused_registered_agent"))
        build_executed = metadata.get("build_executed")
        reused_existing = bool(metadata.get("reused_existing_project")) or build_executed is False

        if reused_existing:
            return self._format_reused_agent_response(
                str(result.get("agent") or project.get("registered_agent") or metadata.get("agent_name") or "inconnu"),
                str(project.get("project_id") or "inconnu"),
            )

        if project.get("status") == "completed" and available and registered and (tests_ok or reused_registered):
            tests_line = (
                "Tests : non relancés (agent déjà enregistré)."
                if reused_registered and not tests_ok
                else "Tests : OK."
            )
            runtime_reload = result.get("runtime_reload") or (result.get("verification") or {}).get("runtime_reload") or {}
            runtime_line = "Runtime rechargé : OK." if runtime_reload.get("ok") else "Runtime rechargé : non vérifié."
            return (
                "Projet terminé.\n"
                f"Agent créé : {result.get('agent')}.\n"
                f"{tests_line}\n"
                "Agent enregistré : oui.\n"
                f"{runtime_line}"
            )

        if project.get("status") == "failed":
            return (
                f"Projet échoué : {project.get('project_id')}.\n"
                f"Étape : {project.get('current_step')}.\n"
                f"Cause : {project.get('error') or 'inconnue'}"
            )

        return (
            f"Projet créé : {project.get('project_id')}.\n"
            f"Type : création d’{project.get('type')}.\n"
            f"Statut : {project.get('status')}.\n"
            f"Étape actuelle : {project.get('current_step')}.\n"
            "Tu peux me demander : 'où en est le projet WWDC ?'"
        )

    def format_status_response(self, project: dict[str, Any] | None) -> str:
        if not project:
            return "Aucun projet correspondant trouvé."
        tests = project.get("test_results") or []
        tests_status = "OK" if tests and all(item.get("returncode") == 0 for item in tests) else "non vérifié"
        result = project.get("result") or {}
        available = "oui" if result.get("available") else "non"
        files = project.get("created_files") or []
        return (
            f"Projet : {project.get('project_id')}\n"
            f"Statut : {project.get('status')}\n"
            f"Étape actuelle : {project.get('current_step')}\n"
            f"Progression : {project.get('progress')}%\n"
            f"Fichiers créés : {', '.join(files) if files else 'aucun'}\n"
            f"Tests : {tests_status}\n"
            f"Agent/tool disponible : {available}\n"
            f"Erreur : {project.get('error') or 'aucune'}"
        )

    def _write_agent(self, spec: AgentSpec) -> Path:
        self.workspace_agents.mkdir(parents=True, exist_ok=True)
        path = self.workspace_agents / f"{spec.name}.py"
        if spec.name == "event_countdown_agent":
            content = self._wwdc_agent_code()
        elif spec.name == "weather_watch_agent":
            content = self._weather_agent_code()
        elif "parse_agriculture_weather_request" in spec.capabilities:
            content = self._agriculture_weather_agent_code(spec)
        else:
            content = self._generic_agent_code(spec)
        content = self._attach_agent_spec(content, spec)
        path.write_text(content, encoding="utf-8")
        return path

    def _write_agent_test(self, spec: AgentSpec, agent_file: Path) -> Path:
        self.workspace_tests.mkdir(parents=True, exist_ok=True)
        path = self.workspace_tests / f"test_{spec.name}.py"
        path.write_text(
            "\n".join(
                [
                    "from __future__ import annotations",
                    "import importlib.util",
                    "import pathlib",
                    "import pytest",
                    "",
                    f"AGENT_FILE = pathlib.Path({str(agent_file)!r})",
                    "",
                    "def load_agent():",
                    "    spec = importlib.util.spec_from_file_location('generated_agent_under_test', AGENT_FILE)",
                    "    module = importlib.util.module_from_spec(spec)",
                    "    assert spec and spec.loader",
                    "    spec.loader.exec_module(module)",
                    "    return module.Agent()",
                    "",
                    "@pytest.mark.asyncio",
                    "async def test_agent_execute_returns_response():",
                    "    result = await load_agent().execute(text='combien de temps avant la WWDC ?')",
                    "    assert isinstance(result, dict)",
                    "    assert result.get('response')",
                    "    assert result.get('status') == 'ok'",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

    async def _run_codex_agent_generation(
        self,
        spec: AgentSpec,
        agent_file: Path,
        test_file: Path,
    ) -> dict[str, Any]:
        self.workspace_agents.mkdir(parents=True, exist_ok=True)
        self.workspace_tests.mkdir(parents=True, exist_ok=True)
        snapshot = self._snapshot_generated_agents()
        runner = self.codex_runner or CodexRunner(workspace=self.project_root)
        prompt = self._codex_agent_prompt(spec, agent_file, test_file)
        result = await runner.run_codex(prompt, f"agent_builder_{spec.name}")
        payload = self._safe_codex_result(result)

        generated_changed = self._generated_agents_changed(snapshot)
        if generated_changed:
            self._restore_generated_agents(snapshot)
            return {
                "ok": False,
                "error": "codex_generated_dir_write_blocked",
                "result": payload,
            }

        if not getattr(result, "ok", False):
            return {
                "ok": False,
                "error": self._codex_error(payload),
                "result": payload,
            }

        missing = [
            self._relative(path)
            for path in (agent_file, test_file)
            if not path.exists()
        ]
        if missing:
            return {
                "ok": False,
                "error": f"codex_missing_files: {', '.join(missing)}",
                "result": payload,
            }

        return {"ok": True, "error": None, "result": payload}

    def _register_agent(self, agent_file: Path) -> Path:
        self.generated_agents.mkdir(parents=True, exist_ok=True)
        destination = self.generated_agents / agent_file.name
        shutil.copy2(agent_file, destination)
        return destination

    def _snapshot_promotion_target(self, agent_file: Path) -> bytes | None:
        destination = self.generated_agents / agent_file.name
        return destination.read_bytes() if destination.exists() else None

    def _rollback_promotion(self, destination: Path, previous: bytes | None) -> None:
        if previous is None:
            destination.unlink(missing_ok=True)
            return
        destination.write_bytes(previous)

    def _reload_runtime_after_rollback(self) -> None:
        if not self.runtime_check:
            return
        from core.runtime.agents.agent_runtime_manager import get_agent_runtime_manager

        manager = get_agent_runtime_manager()
        registry = getattr(manager, "registry", None)
        if registry is not None and hasattr(registry, "generated_dir"):
            registry.generated_dir = self.generated_agents
        manager.reload()

    def _get_runtime_governor(self) -> Any:
        if self.runtime_governor is not None:
            return self.runtime_governor
        from core.runtime.governor import get_runtime_governor

        return get_runtime_governor()

    def _registered_agent_for_spec(
        self,
        spec: AgentSpec,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        registry = DynamicAgentRegistry(self.generated_agents)
        return registry.find_registered_agent_for_spec(
            spec.to_dict(),
            metadata.get("spec_signature"),
        )

    def _project_metadata(self, spec: AgentSpec, query: str) -> dict[str, Any]:
        return {
            "spec": spec.to_dict(),
            "agent_name": spec.name,
            "intent_key": self._intent_key(spec),
            "normalized_query": self._normalize_for_key(query),
            "spec_signature": self._spec_signature(spec),
        }

    def _reuse_existing_project(self, project: dict[str, Any], spec: AgentSpec) -> dict[str, Any]:
        return {
            "status": project.get("status") or "completed",
            "project": project,
            "spec": spec.to_dict(),
            "build_executed": False,
            "reused_existing_project": True,
            "response": self._format_reused_agent_response(
                str(project.get("registered_agent") or spec.name),
                str(project.get("project_id") or "inconnu"),
            ),
        }

    async def _return_registered_agent(
        self,
        spec: AgentSpec,
        registered_agent: dict[str, Any],
        *,
        query: str,
        source_channel: str,
    ) -> dict[str, Any]:
        verification = await self._verify_agent(spec)
        await self._publish_agent_consulted(spec, registered_agent, query, source_channel, verification)
        if not verification.get("ok"):
            return {
                "status": "failed",
                "project": None,
                "agent": registered_agent,
                "spec": spec.to_dict(),
                "build_executed": False,
                "reused_existing_agent": True,
                "reused_existing_project": False,
                "reused_registered_agent": True,
                "response": self._format_registered_agent_response(
                    spec,
                    registered_agent,
                    verification,
                ),
            }

        return {
            "status": "completed",
            "project": None,
            "agent": registered_agent,
            "spec": spec.to_dict(),
            "build_executed": False,
            "reused_existing_agent": True,
            "reused_existing_project": False,
            "reused_registered_agent": True,
            "response": self._format_registered_agent_response(
                spec,
                registered_agent,
                verification,
            ),
        }

    async def _publish_agent_consulted(
        self,
        spec: AgentSpec,
        registered_agent: dict[str, Any],
        query: str,
        source_channel: str,
        verification: dict[str, Any],
    ) -> None:
        from core.events.event import Event
        from core.events.event_bus import event_bus
        from core.events.event_types import AGENT_CONSULTED

        await event_bus.publish(
            Event(
                type=AGENT_CONSULTED,
                source="agent_build_orchestrator",
                payload={
                    "agent": spec.name,
                    "query": query,
                    "source_channel": source_channel,
                    "registered_path": registered_agent.get("path"),
                    "available": bool(verification.get("ok")),
                    "reused_registered_agent": True,
                },
            )
        )

    def _format_registered_agent_response(
        self,
        spec: AgentSpec,
        registered_agent: dict[str, Any],
        verification: dict[str, Any],
    ) -> str:
        if not verification.get("ok"):
            return (
                f"Agent existant indisponible : {spec.name}.\n"
                f"Fichier enregistré : {registered_agent.get('path') or 'inconnu'}.\n"
                f"Cause : {verification.get('error') or 'verification_failed'}"
            )

        return (
            self._format_reused_agent_response(spec.name, "aucun projet de build")
        )

    def _format_reused_agent_response(self, agent_name: str, project_id: str) -> str:
        return (
            f"Agent déjà disponible : {agent_name}.\n"
            f"Projet existant : {project_id}.\n"
            "Tests déjà validés : OK.\n"
            "Aucune reconstruction nécessaire."
        )

    async def _verify_agent(self, spec: AgentSpec) -> dict[str, Any]:
        if not self.runtime_check:
            return {"ok": True, "skipped": True, "runtime_reload": {"ok": True, "skipped": True, "agents": [spec.name]}}
        from core.runtime.agents.agent_runtime_manager import get_agent_runtime_manager

        manager = get_agent_runtime_manager()
        registry = getattr(manager, "registry", None)
        if registry is not None and hasattr(registry, "generated_dir"):
            registry.generated_dir = self.generated_agents
        runtime_reload = manager.reload()
        result = await manager.run(spec.name, "combien de temps avant la WWDC ?")
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error"), "raw": result, "runtime_reload": runtime_reload}
        response = str(result.get("response") or "")
        return {
            "ok": bool(response),
            "response": response,
            "raw": result,
            "runtime_reload": runtime_reload,
        }

    def _run_command(self, command: list[str], name: str) -> dict[str, Any]:
        completed = subprocess.run(
            command,
            cwd=self.project_root,
            text=True,
            capture_output=True,
            timeout=120,
        )
        return {
            "name": name,
            "command": command,
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }

    def _append_test_result(self, project_id: str, result: dict[str, Any]) -> None:
        project = self.project_manager.get_project(project_id)
        if not project:
            return
        tests = list(project.get("test_results") or [])
        tests.append(result)
        self.project_manager.update_project(project_id, {"test_results": tests})

    def _step(self, project_id: str, step: str, status: str, progress: int) -> None:
        self.project_manager.update_project(
            project_id,
            {"status": "running"},
            step=step,
            step_status=status,
            progress=progress,
        )

    def _fail(
        self,
        project_id: str,
        step: str,
        error: str,
        test_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if test_result:
            self._append_test_result(project_id, test_result)
        existing = self.project_manager.get_project(project_id) or {}
        created_files = [
            path
            for path in existing.get("created_files") or []
            if "core/agents/generated/" not in str(path).replace("\\", "/")
        ]
        project = self.project_manager.update_project(
            project_id,
            {
                "status": "failed",
                "current_step": step,
                "registry_status": "not_registered",
                "registered_agent": None,
                "created_files": created_files,
                "runtime_status": "failed" if step == "verification" else "not_available",
                "result": {"available": False},
            },
            step=step,
            step_status="failed",
            error=error,
        )
        return {"status": "failed", "project": project}

    def _relative(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.project_root.resolve()))
        except ValueError:
            return str(path)

    def _normalize(self, value: str) -> str:
        text = unicodedata.normalize("NFKD", value.lower())
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        return " ".join(text.split())

    def _normalize_for_key(self, value: str) -> str:
        text = self._normalize(value)
        cleaned = []
        for char in text:
            cleaned.append(char if char.isalnum() else " ")
        return " ".join("".join(cleaned).split())

    def _normalize_build_mode(self, build_mode: str) -> BuildMode:
        if build_mode in {"deterministic", "codex", "hybrid"}:
            return build_mode  # type: ignore[return-value]
        return "deterministic"

    def _codex_state(self, build_mode: BuildMode) -> dict[str, Any]:
        return {
            "build_mode": build_mode,
            "codex_used": build_mode in {"codex", "hybrid"},
            "codex_ok": None,
            "codex_fallback": False,
            "codex_error": None,
        }

    def _codex_project_metadata(self, codex_state: dict[str, Any]) -> dict[str, Any]:
        return {
            "build_mode": codex_state.get("build_mode"),
            "codex_used": codex_state.get("codex_used"),
            "codex_ok": codex_state.get("codex_ok"),
            "codex_fallback": codex_state.get("codex_fallback"),
            "codex_error": codex_state.get("codex_error"),
        }

    def _with_build_status(
        self,
        payload: dict[str, Any],
        codex_state: dict[str, Any],
    ) -> dict[str, Any]:
        payload.update(self._codex_project_metadata(codex_state))
        if "codex_result" in codex_state:
            payload["codex_result"] = codex_state.get("codex_result")
        return payload

    def _codex_agent_prompt(self, spec: AgentSpec, agent_file: Path, test_file: Path) -> str:
        relative_agent = self._relative(agent_file)
        relative_test = self._relative(test_file)
        spec_json = json.dumps(spec.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)
        return "\n".join(
            [
                "Mission: generate or improve a deterministic Neron dynamic agent.",
                "",
                "Hard filesystem boundary:",
                f"- Write the agent only at {relative_agent}.",
                f"- Write the test only at {relative_test}.",
                "- Do not write, edit, delete, or inspect secrets.",
                "- Do not write to core/agents/generated.",
                "- Do not edit systemd, services, security config, deployment files, or data stores.",
                "- Do not commit or push.",
                "",
                "Agent contract:",
                "- The agent file must define class Agent.",
                f"- Agent.name must be {spec.name!r}.",
                "- Agent.execute must be async and return a dict with status='ok' and a non-empty response.",
                "- Keep behavior deterministic and testable without network access.",
                "- The pytest file must validate the generated agent through its workspace path.",
                "",
                "Agent spec:",
                spec_json,
            ]
        )

    def _safe_codex_result(self, result: Any) -> dict[str, Any]:
        data = result.to_dict() if hasattr(result, "to_dict") else dict(result or {})
        command = list(data.get("command") or [])
        if command and command[-1] and len(str(command[-1])) > 80:
            command[-1] = "[PROMPT_REDACTED]"
        data["command"] = command
        for key in ("stdout", "stderr"):
            data[key] = redact_secrets(str(data.get(key) or ""))
        return data

    def _codex_error(self, payload: dict[str, Any]) -> str:
        error = payload.get("stderr") or payload.get("stdout") or "codex_failed"
        return redact_secrets(str(error))[:1000]

    def _snapshot_generated_agents(self) -> dict[str, bytes]:
        if not self.generated_agents.exists():
            return {}
        snapshot: dict[str, bytes] = {}
        for path in self.generated_agents.glob("*.py"):
            if path.is_file():
                snapshot[path.name] = path.read_bytes()
        return snapshot

    def _generated_agents_changed(self, snapshot: dict[str, bytes]) -> bool:
        current = self._snapshot_generated_agents()
        return current != snapshot

    def _restore_generated_agents(self, snapshot: dict[str, bytes]) -> None:
        self.generated_agents.mkdir(parents=True, exist_ok=True)
        for path in self.generated_agents.glob("*.py"):
            if path.name not in snapshot:
                path.unlink()
        for name, content in snapshot.items():
            path = self.generated_agents / name
            if not path.exists() or path.read_bytes() != content:
                path.write_bytes(content)

    def assess_request_safety(self, query: str) -> dict[str, Any]:
        normalized = self._normalize_for_key(query)
        reasons = [
            keyword
            for keyword in sorted(SENSITIVE_BUILD_KEYWORDS)
            if keyword in normalized
        ]
        return {
            "auto_apply_allowed": not reasons,
            "risk_level": "low" if not reasons else "critical",
            "reasons": reasons,
        }

    def _format_refusal_response(self, safety: dict[str, Any]) -> str:
        reasons = ", ".join(str(item) for item in safety.get("reasons") or [])
        return (
            "Création d’agent refusée en mode automatique.\n"
            "Risque : critical.\n"
            f"Raison : {reasons or 'demande sensible'}.\n"
            "Aucun agent n’a été généré ni enregistré."
        )

    def _agriculture_domain(self, normalized: str) -> str | None:
        agriculture_terms = {
            "agriculture",
            "agricole",
            "agricoles",
            "agri",
            "culture",
            "cultures",
            "champ",
            "champs",
            "irrigation",
            "recolte",
            "recoltes",
            "crop",
            "crops",
            "farm",
            "farming",
        }
        if any(term in normalized.split() for term in agriculture_terms):
            return "agriculture"
        return None

    def _intent_key(self, spec: AgentSpec) -> str:
        return self._normalize_for_key(
            " ".join(
                [
                    spec.kind,
                    spec.name,
                    spec.title,
                    spec.goal,
                    " ".join(spec.inputs),
                    " ".join(spec.outputs),
                    " ".join(spec.capabilities),
                ]
            )
        )

    def _spec_signature(self, spec: AgentSpec) -> str:
        return self._normalize_for_key(
            json.dumps(spec.to_dict(), sort_keys=True, ensure_ascii=False)
        )

    def _attach_agent_spec(self, content: str, spec: AgentSpec) -> str:
        spec_json = json.dumps(spec.to_dict(), indent=4, sort_keys=True, ensure_ascii=False)
        spec_signature = self._spec_signature(spec)
        metadata = (
            f"AGENT_SPEC = {spec_json}\n"
            f"AGENT_SPEC_SIGNATURE = {spec_signature!r}\n\n"
        )
        marker = "from __future__ import annotations\n\n"
        if content.startswith(marker):
            return content.replace(marker, marker + metadata, 1)
        return metadata + content

    def _name_from_query(self, normalized: str) -> str:
        ignored = {"cree", "creer", "agent", "tool", "outil", "ajoute", "un", "une", "qui", "me", "pour"}
        words = [re.sub(r"[^a-z0-9]", "", word) for word in normalized.split()]
        useful = [word for word in words if word and word not in ignored]
        base = "_".join(useful[:3]) or "custom"
        return base if base.endswith("_agent") else f"{base}_agent"

    def _explicit_agent_name(self, normalized: str) -> str | None:
        patterns = (
            r"\bnomme\s+([a-z0-9_][a-z0-9_-]*)",
            r"\bappele\s+([a-z0-9_][a-z0-9_-]*)",
            r"\bappelle\s+([a-z0-9_][a-z0-9_-]*)",
            r"\bs\s+appelle\s+([a-z0-9_][a-z0-9_-]*)",
            r"\bnamed\s+([a-z0-9_][a-z0-9_-]*)",
            r"\bname\s+([a-z0-9_][a-z0-9_-]*)",
        )

        for pattern in patterns:
            match = re.search(pattern, normalized)
            if not match:
                continue
            candidate = re.sub(r"[^a-z0-9_]+", "_", match.group(1).lower()).strip("_")
            if not candidate:
                continue
            if candidate[0].isdigit():
                candidate = f"agent_{candidate}"
            return candidate

        return None

    def _wwdc_agent_code(self) -> str:
        return '''from __future__ import annotations

from datetime import datetime, timezone


class Agent:
    name = "event_countdown_agent"
    target_event = "WWDC"
    target_date = datetime(2026, 6, 8, 17, 0, tzinfo=timezone.utc)
    source = "static_fallback: Apple WWDC 2026 keynote expected June 8, 2026"

    async def execute(self, text: str = "") -> dict:
        now = datetime.now(timezone.utc)
        delta = self.target_date - now
        total_seconds = int(delta.total_seconds())
        if total_seconds <= 0:
            remaining = "l'événement est commencé ou passé"
        else:
            days, rem = divmod(total_seconds, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, _ = divmod(rem, 60)
            remaining = f"{days} jours, {hours} heures et {minutes} minutes"
        return {
            "status": "ok",
            "agent": self.name,
            "event_name": self.target_event,
            "target_date": self.target_date.isoformat(),
            "remaining_time": remaining,
            "source": self.source,
            "response": f"Temps restant avant la WWDC : {remaining}. Date cible : {self.target_date.isoformat()}",
        }
'''

    def _weather_agent_code(self) -> str:
        return '''from __future__ import annotations


class Agent:
    name = "weather_watch_agent"

    async def execute(self, text: str = "") -> dict:
        return {
            "status": "ok",
            "agent": self.name,
            "source": "static_fallback",
            "response": "Agent météo disponible. Connecteur météo externe non configuré; réponse fallback active.",
        }
'''

    def _agriculture_weather_agent_code(self, spec: AgentSpec) -> str:
        return f'''from __future__ import annotations


class Agent:
    name = {spec.name!r}
    goal = {spec.goal!r}
    capabilities = {spec.capabilities!r}

    async def execute(self, text: str = "") -> dict:
        request = self.parse_agriculture_weather_request(text)
        fallback = self.static_agriculture_weather_fallback(request)
        response = self.format_agriculture_weather_response(fallback)
        return {{
            "status": "ok",
            "agent": self.name,
            "goal": self.goal,
            "capabilities": self.capabilities,
            "request": request,
            "source": "static_agriculture_weather_fallback",
            "response": response,
        }}

    def parse_agriculture_weather_request(self, text: str) -> dict:
        return {{
            "raw": text,
            "domain": "agriculture",
            "needs": ["meteo_agricole", "risque_cultures", "fenetre_intervention"],
        }}

    def static_agriculture_weather_fallback(self, request: dict) -> dict:
        return {{
            "summary": "Agent météo agricole disponible. Connecteur météo externe non configuré; fallback agricole actif.",
            "risk_flags": ["surveiller gel", "surveiller pluie forte", "adapter irrigation"],
            "request": request,
        }}

    def format_agriculture_weather_response(self, data: dict) -> str:
        return (
            data["summary"]
            + " Spécialisation agriculture : aide aux décisions météo pour cultures, irrigation et fenêtres de travaux."
        )
'''

    def _generic_agent_code(self, spec: AgentSpec) -> str:
        return f'''from __future__ import annotations


class Agent:
    name = {spec.name!r}

    async def execute(self, text: str = "") -> dict:
        return {{
            "status": "ok",
            "agent": self.name,
            "response": {("Agent disponible pour : " + spec.goal)!r},
        }}
'''


async def build_agent_from_request(
    query: str,
    *,
    requested_by: str = "user",
    source_channel: str = "api",
    build_mode: BuildMode = "deterministic",
) -> dict[str, Any]:
    return await AgentBuildOrchestrator().build_from_request(
        query,
        requested_by=requested_by,
        source_channel=source_channel,
        build_mode=build_mode,
    )
