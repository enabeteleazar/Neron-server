from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import subprocess
import tokenize
from pathlib import Path
from typing import Any

from modules.evolution.models import EvolutionProposal


TODO_MARKER_RE = re.compile(r"(?<![A-Za-z0-9_/])(?:TODO|FIXME)(?::|\s|$)")


class ProposalEngine:
    def __init__(self, workspace: Path = Path("/etc/neron")) -> None:
        self.workspace = workspace

    def observe(self) -> dict[str, Any]:
        projects = self._load_projects()
        todos = self._scan_todos()
        generated_agents = sorted(
            str(path.relative_to(self.workspace))
            for path in (self.workspace / "core" / "agents" / "generated").glob("*.py")
            if path.name != "__init__.py"
        )
        return {
            "projects": {
                "count": len(projects),
                "failed": [project for project in projects if project.get("status") == "failed"][:10],
                "running": [project for project in projects if project.get("status") == "running"][:10],
            },
            "generated_agents": generated_agents,
            "todos": todos,
            "routes": self._route_snapshot(),
            "git": self._git_snapshot(),
            "docs": {
                "evolution_supervisor": (
                    self.workspace / "docs" / "architecture" / "evolution_supervisor.md"
                ).exists()
            },
        }

    def detect_limits(self, observation: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        observation = observation or self.observe()
        limits: list[dict[str, Any]] = []

        if observation["generated_agents"] and not self._dynamic_agents_are_routed():
            limits.append(
                {
                    "kind": "agents_created_but_not_routed",
                    "severity": "recommended",
                    "summary": "Des agents générés existent mais le routage dynamique n'est pas visible avant le fallback LLM.",
                    "areas": ["core/pipeline/routing", "core/agents/conversation", "core/agent_factory"],
                }
            )

        failed_projects = observation["projects"]["failed"]
        if failed_projects:
            limits.append(
                {
                    "kind": "failed_projects",
                    "severity": "recommended",
                    "summary": f"{len(failed_projects)} projet(s) en échec récent nécessitent une analyse.",
                    "areas": ["core/projects", "core/agent_factory", "data/projects.json"],
                }
            )

        if observation["todos"]:
            limits.append(
                {
                    "kind": "todo_fixme",
                    "severity": "future",
                    "summary": f"{len(observation['todos'])} TODO/FIXME détecté(s) dans le code suivi.",
                    "areas": sorted({item["file"] for item in observation["todos"][:8]}),
                }
            )

        expected_routes = {
            "/evolution/status",
            "/evolution/propose",
            "/evolution/proposals",
            "/evolution/runs",
        }
        missing_routes = sorted(expected_routes - set(observation["routes"]))
        if missing_routes:
            limits.append(
                {
                    "kind": "routes_missing",
                    "severity": "recommended",
                    "summary": "Des endpoints d'évolution supervisée sont absents.",
                    "areas": ["modules/evolution/routes.py", "core/app.py"],
                    "missing_routes": missing_routes,
                }
            )

        if not observation["docs"]["evolution_supervisor"]:
            limits.append(
                {
                    "kind": "docs_missing",
                    "severity": "future",
                    "summary": "La documentation d'architecture EvolutionSupervisor est absente.",
                    "areas": ["docs/architecture/evolution_supervisor.md"],
                }
            )

        return limits

    def generate_proposals(
        self,
        observation: dict[str, Any] | None = None,
        limits: list[dict[str, Any]] | None = None,
    ) -> list[EvolutionProposal]:
        observation = observation or self.observe()
        limits = limits if limits is not None else self.detect_limits(observation)
        proposals: list[EvolutionProposal] = []

        for limit in limits:
            kind = limit.get("kind")
            if kind == "agents_created_but_not_routed":
                proposals.append(self._proposal_dynamic_agent_routing(limit))
            elif kind == "failed_projects":
                proposals.append(self._proposal_failed_projects(limit))
            elif kind == "todo_fixme":
                proposals.append(self._proposal_todos(limit, observation))
            elif kind == "routes_missing":
                proposals.append(self._proposal_routes(limit))
            elif kind == "docs_missing":
                proposals.append(self._proposal_docs(limit))

        proposals.extend(self._fallback_proposals())
        deduped: list[EvolutionProposal] = []
        seen_titles: set[str] = set()
        for proposal in proposals:
            if proposal.title in seen_titles:
                continue
            seen_titles.add(proposal.title)
            deduped.append(proposal)
            if len(deduped) == 3:
                break
        return deduped

    def _proposal_dynamic_agent_routing(self, limit: dict[str, Any]) -> EvolutionProposal:
        return self._make_proposal(
            "Router les agents dynamiques avant fallback LLM",
            priority="recommended",
            proposal_type="feature",
            summary="Brancher les agents générés et enregistrés dans le routage conversationnel avant l'appel LLM générique.",
            expected_gain="Les agents créés deviennent utilisables naturellement depuis Telegram et l'API.",
            risk="medium",
            areas=limit["areas"],
            acceptance_criteria=[
                "Une requête correspondant à un agent généré déclenche cet agent avant le LLM.",
                "Un test couvre la découverte et l'exécution d'un agent enregistré.",
                "Le fallback LLM reste inchangé quand aucun agent ne correspond.",
            ],
            estimate="medium",
        )

    def _proposal_failed_projects(self, limit: dict[str, Any]) -> EvolutionProposal:
        return self._make_proposal(
            "Diagnostiquer les projets en échec",
            priority="recommended",
            proposal_type="bugfix",
            summary=limit["summary"],
            expected_gain="Réduire les blocages récurrents et clarifier les causes d'échec des workflows suivis.",
            risk="medium",
            areas=limit["areas"],
            acceptance_criteria=[
                "Les projets failed récents sont catégorisés par cause probable.",
                "Un rapport court est disponible dans ProjectManager ou les logs.",
                "Aucun projet n'est relancé automatiquement sans validation.",
            ],
            estimate="medium",
        )

    def _proposal_todos(self, limit: dict[str, Any], observation: dict[str, Any]) -> EvolutionProposal:
        areas = limit["areas"] or ["core"]
        todo_sample = "; ".join(
            f"{item['file']}:{item['line']}" for item in observation["todos"][:5]
        )
        return self._make_proposal(
            "Traiter les TODO/FIXME prioritaires",
            priority="future",
            proposal_type="refactor",
            summary=f"Analyser et traiter les TODO/FIXME les plus proches des modules actifs. Exemples: {todo_sample}",
            expected_gain="Dette technique plus visible et moins de comportements implicites non finalisés.",
            risk="low",
            areas=areas,
            acceptance_criteria=[
                "Les TODO/FIXME retenus sont supprimés ou transformés en issue/proposition claire.",
                "Les changements de comportement sont couverts par test quand nécessaire.",
                "Aucune refactorisation large sans justification locale.",
            ],
            estimate="small",
        )

    def _proposal_routes(self, limit: dict[str, Any]) -> EvolutionProposal:
        missing = ", ".join(limit.get("missing_routes") or [])
        return self._make_proposal(
            "Exposer les endpoints EvolutionSupervisor",
            priority="recommended",
            proposal_type="feature",
            summary=f"Ajouter les routes API manquantes pour consulter, proposer, accepter, refuser et arrêter les évolutions. Manquantes: {missing}",
            expected_gain="L'évolution supervisée devient pilotable depuis l'API sans dépendre d'un service externe.",
            risk="medium",
            areas=limit["areas"],
            acceptance_criteria=[
                "Les endpoints /evolution/status, /propose, /proposals, /accept, /reject, /stop et /runs répondent.",
                "Accepter une proposition crée un run de type evolution.",
                "Une mission running empêche le lancement d'une seconde mission.",
            ],
            estimate="medium",
        )

    def _proposal_docs(self, limit: dict[str, Any]) -> EvolutionProposal:
        return self._make_proposal(
            "Documenter la boucle d'évolution supervisée",
            priority="future",
            proposal_type="docs",
            summary=limit["summary"],
            expected_gain="Les règles de validation humaine, d'exécution Codex et de tests deviennent explicites.",
            risk="low",
            areas=limit["areas"],
            acceptance_criteria=[
                "La documentation décrit la boucle proposer -> accepter -> exécuter -> tester -> commit/push.",
                "Les commandes Telegram et endpoints API sont listés.",
                "Les limites V1 et garanties de sécurité sont documentées.",
            ],
            estimate="small",
        )

    def _fallback_proposals(self) -> list[EvolutionProposal]:
        return [
            self._make_proposal(
                "Renforcer les tests des workflows suivis",
                priority="recommended",
                proposal_type="test",
                summary="Ajouter des tests de non-régression autour des workflows projets, agents générés et routage.",
                expected_gain="Moins de régressions sur les chemins Telegram/API critiques.",
                risk="low",
                areas=["tests", "core/projects", "core/agent_factory"],
                acceptance_criteria=[
                    "Les workflows projet et agent généré ont des tests ciblés.",
                    "Les tests n'appellent aucun service externe obligatoire.",
                    "pytest tests/test_tracked_agent_workflow.py -v reste vert.",
                ],
                estimate="medium",
            ),
            self._make_proposal(
                "Centraliser les incohérences registry/projects/agents",
                priority="future",
                proposal_type="refactor",
                summary="Créer un diagnostic simple qui compare agents générés, registry runtime et projets suivis.",
                expected_gain="Repérer rapidement les agents créés mais non disponibles ou les projets sans état cohérent.",
                risk="medium",
                areas=["core/agent_factory", "core/runtime/agents", "core/projects"],
                acceptance_criteria=[
                    "Un diagnostic liste les agents générés, enregistrés et routables.",
                    "Les projets agent_creation référencent clairement leur agent.",
                    "Aucune mutation d'état n'est faite par le diagnostic.",
                ],
                estimate="medium",
            ),
            self._make_proposal(
                "Clarifier les responsabilités d'architecture",
                priority="future",
                proposal_type="docs",
                summary="Mettre à jour la documentation des responsabilités entre pipeline, gateway, agents et projets.",
                expected_gain="Les futures évolutions touchent les bons modules avec moins de doublons.",
                risk="low",
                areas=["docs/architecture", "core/README.md"],
                acceptance_criteria=[
                    "Les responsabilités des modules centraux sont décrites.",
                    "Les flux Telegram/API vers AgentRouter sont explicités.",
                    "Les limites connues sont listées sans prétendre les résoudre.",
                ],
                estimate="small",
            ),
        ]

    def _make_proposal(
        self,
        title: str,
        *,
        priority: str,
        proposal_type: str,
        summary: str,
        expected_gain: str,
        risk: str,
        areas: list[str],
        acceptance_criteria: list[str],
        estimate: str,
    ) -> EvolutionProposal:
        prompt = (
            "Tu travailles sur le projet Néron OS dans /etc/neron.\n\n"
            f"Mission validée par l'utilisateur: {title}\n\n"
            f"Résumé: {summary}\n"
            f"Gain attendu: {expected_gain}\n"
            f"Risque: {risk}\n"
            f"Zones probablement concernées: {', '.join(areas)}\n\n"
            "Contraintes:\n"
            "- Lire le code existant avant modification.\n"
            "- Garder les changements ciblés et compatibles avec les endpoints existants.\n"
            "- Ne jamais utiliser Obsidian comme stockage opérationnel.\n"
            "- Ajouter ou ajuster les tests pertinents.\n"
            "- Lancer les validations utiles et rapporter les résultats.\n\n"
            "Critères d'acceptation:\n"
            + "\n".join(f"- {criterion}" for criterion in acceptance_criteria)
        )
        digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:6]
        return EvolutionProposal(
            proposal_id=f"evo_{digest}",
            title=title,
            priority=priority,
            type=proposal_type,
            summary=summary,
            expected_gain=expected_gain,
            risk=risk,
            areas=areas,
            acceptance_criteria=acceptance_criteria,
            codex_prompt=prompt,
            estimate=estimate,
        )

    def _load_projects(self) -> list[dict[str, Any]]:
        path = self.workspace / "data" / "projects.json"
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        projects = data.get("projects", []) if isinstance(data, dict) else []
        return projects if isinstance(projects, list) else []

    def _scan_todos(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        roots = [self.workspace / "core", self.workspace / "tests", self.workspace / "docs"]
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "__pycache__" in path.parts:
                    continue
                self._collect_todos(path, results)
                if len(results) >= 30:
                    return results
            for path in root.rglob("*.md"):
                self._collect_todos(path, results)
                if len(results) >= 30:
                    return results
        return results

    def _collect_todos(self, path: Path, results: list[dict[str, Any]]) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        lines = text.splitlines()

        if path.suffix == ".py":
            self._collect_python_todos(path, text, lines, results)
            return

        for line_number, line in enumerate(lines, start=1):
            self._append_todo_if_present(path, line_number, line, results)
            if len(results) >= 30:
                return

    def _collect_python_todos(
        self,
        path: Path,
        text: str,
        lines: list[str],
        results: list[dict[str, Any]],
    ) -> None:
        docstring_lines = self._python_docstring_lines(text)

        try:
            tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        except tokenize.TokenError:
            tokens = iter(())

        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            self._append_todo_if_present(
                path,
                token.start[0],
                lines[token.start[0] - 1],
                results,
            )
            if len(results) >= 30:
                return

        for line_number in sorted(docstring_lines):
            if line_number <= len(lines):
                self._append_todo_if_present(path, line_number, lines[line_number - 1], results)
                if len(results) >= 30:
                    return

    def _python_docstring_lines(self, text: str) -> set[int]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return set()

        lines: set[int] = set()

        for node in ast.walk(tree):
            if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.body:
                continue

            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                start = getattr(first, "lineno", None)
                end = getattr(first, "end_lineno", start)
                if start is not None and end is not None:
                    lines.update(range(start, end + 1))

        return lines

    def _append_todo_if_present(
        self,
        path: Path,
        line_number: int,
        line: str,
        results: list[dict[str, Any]],
    ) -> None:
        if not TODO_MARKER_RE.search(line):
            return

        results.append(
            {
                "file": str(path.relative_to(self.workspace)),
                "line": line_number,
                "text": line.strip()[:160],
            }
        )

    def _route_snapshot(self) -> list[str]:
        paths: set[str] = set()
        for path in [self.workspace / "core" / "app.py", self.workspace / "core" / "evolution" / "routes.py"]:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for route in (
                "/evolution/status",
                "/evolution/propose",
                "/evolution/proposals",
                "/evolution/accept",
                "/evolution/reject",
                "/evolution/stop",
                "/evolution/runs",
            ):
                if route in text:
                    paths.add(route)
        return sorted(paths)

    def _git_snapshot(self) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                cwd=self.workspace,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
        except Exception as exc:
            return {"recent_commits": [], "error": str(exc)}
        return {
            "recent_commits": result.stdout.splitlines(),
            "error": result.stderr.strip() or None,
        }

    def _dynamic_agents_are_routed(self) -> bool:
        candidates = [
            self.workspace / "core" / "app.py",
            self.workspace / "core" / "pipeline" / "routing" / "agent_router.py",
            self.workspace / "core" / "agents" / "conversation" / "conversation_agent.py",
        ]
        haystack = "\n".join(
            path.read_text(encoding="utf-8", errors="replace") for path in candidates if path.exists()
        )
        return "delegate_to_registered_agent" in haystack and "list_agent_records" in haystack
