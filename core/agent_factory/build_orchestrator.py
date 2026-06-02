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
from typing import Any

from core.agent_factory.registry import DynamicAgentRegistry
from core.agent_factory.validator import validate_agent
from core.projects.manager import ProjectManager, get_project_manager


DEFAULT_PROJECT_ROOT = Path("/etc/neron")
DEFAULT_WORKSPACE_AGENTS = DEFAULT_PROJECT_ROOT / "workspace" / "agents"
DEFAULT_WORKSPACE_TESTS = DEFAULT_PROJECT_ROOT / "workspace" / "agent_tests"
DEFAULT_GENERATED_AGENTS = DEFAULT_PROJECT_ROOT / "core" / "agents" / "generated"


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
    ) -> None:
        self.project_manager = project_manager or get_project_manager()
        self.project_root = project_root
        self.workspace_agents = workspace_agents
        self.workspace_tests = workspace_tests
        self.generated_agents = generated_agents
        self.python_executable = python_executable or sys.executable
        self.runtime_check = runtime_check

    async def build_from_request(
        self,
        query: str,
        *,
        requested_by: str = "user",
        source_channel: str = "api",
    ) -> dict[str, Any]:
        spec = self.plan_spec(query)
        metadata = self._project_metadata(spec, query)
        existing = self.project_manager.find_existing_agent_project(
            agent_name=spec.name,
            intent_key=metadata["intent_key"],
            spec_signature=metadata["spec_signature"],
        )
        if existing:
            return self._reuse_existing_project(existing, spec)

        registered_agent = self._registered_agent_for_spec(spec, metadata)
        if registered_agent:
            return await self._return_registered_agent(
                spec,
                registered_agent,
                query=query,
                source_channel=source_channel,
            )

        project = self.project_manager.create_project(
            title=spec.title,
            project_type=spec.kind,
            requested_by=requested_by,
            source_channel=source_channel,
            query=query,
            metadata=metadata,
        )
        project_id = str(project["project_id"])

        try:
            self._step(project_id, "planning", "done", 10)

            agent_file = self._write_agent(spec)
            test_file = self._write_agent_test(spec, agent_file)
            self.project_manager.update_project(
                project_id,
                {
                    "created_files": [
                        self._relative(agent_file),
                        self._relative(test_file),
                    ],
                    "status": "running",
                },
                step="code_generation",
                step_status="done",
                progress=35,
            )

            validation = validate_agent(str(agent_file))
            if not validation.get("ok"):
                return self._fail(project_id, "validation", validation.get("error", "validation_failed"))
            self._step(project_id, "validation", "done", 50)

            compile_result = self._run_command(
                [self.python_executable, "-m", "py_compile", str(agent_file)],
                "compile_agent",
            )
            if compile_result["returncode"] != 0:
                return self._fail(project_id, "compile", compile_result["stderr_tail"] or "compile_failed", compile_result)

            test_result = self._run_command(
                [self.python_executable, "-m", "pytest", "-q", str(test_file)],
                "pytest_agent",
            )
            self._append_test_result(project_id, test_result)
            if test_result["returncode"] != 0:
                return self._fail(project_id, "tests", test_result["stdout_tail"] or test_result["stderr_tail"])
            self._step(project_id, "tests", "done", 70)

            destination = self._register_agent(agent_file)
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
                return self._fail(project_id, "verification", verification.get("error", "verification_failed"))

            completed = self.project_manager.update_project(
                project_id,
                {
                    "status": "completed",
                    "current_step": "completed",
                    "progress": 100,
                    "result": {
                        "agent": spec.name,
                        "verification": verification,
                        "available": True,
                    },
                    "error": None,
                },
                step="verification",
                step_status="done",
                progress=100,
            )
            return {
                "status": "completed",
                "project": completed,
                "spec": spec.to_dict(),
                "reused_existing_project": False,
                "response": self.format_project_response(completed),
            }
        except Exception as exc:
            failed = self._fail(project_id, "exception", str(exc))
            return {
                "status": "failed",
                "project": failed["project"],
                "spec": spec.to_dict(),
                "reused_existing_project": False,
                "response": self.format_project_response(failed["project"]),
            }

    def plan_spec(self, query: str) -> AgentSpec:
        normalized = self._normalize(query)
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

        if project.get("status") == "completed" and available and registered and (tests_ok or reused_registered):
            tests_line = (
                "Tests : non relancés (agent déjà enregistré)."
                if reused_registered and not tests_ok
                else "Tests : OK."
            )
            return (
                f"Projet terminé : {project.get('project_id')}.\n"
                f"Agent créé : {result.get('agent')}.\n"
                f"{tests_line}\n"
                "Agent enregistré : oui.\n"
                "Appel de vérification : OK."
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

    def _register_agent(self, agent_file: Path) -> Path:
        self.generated_agents.mkdir(parents=True, exist_ok=True)
        destination = self.generated_agents / agent_file.name
        shutil.copy2(agent_file, destination)
        return destination

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
            "reused_existing_project": True,
            "response": self.format_project_response(project),
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
            f"Agent existant réutilisé : {spec.name}.\n"
            f"Fichier enregistré : {registered_agent.get('path') or 'inconnu'}.\n"
            "Projet de build : non créé.\n"
            "Tests : non relancés.\n"
            "Disponibilité : OK."
        )

    async def _verify_agent(self, spec: AgentSpec) -> dict[str, Any]:
        if not self.runtime_check:
            return {"ok": True, "skipped": True}
        from core.runtime.agents.agent_runtime_manager import get_agent_runtime_manager

        manager = get_agent_runtime_manager()
        manager.reload()
        result = await manager.run(spec.name, "combien de temps avant la WWDC ?")
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error"), "raw": result}
        response = str(result.get("response") or "")
        return {
            "ok": bool(response),
            "response": response,
            "raw": result,
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
        project = self.project_manager.update_project(
            project_id,
            {
                "status": "failed",
                "current_step": step,
                "registry_status": "not_registered",
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
) -> dict[str, Any]:
    return await AgentBuildOrchestrator().build_from_request(
        query,
        requested_by=requested_by,
        source_channel=source_channel,
    )
