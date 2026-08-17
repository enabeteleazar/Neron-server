from __future__ import annotations

import ast
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.runtime.store import AgentRuntimeStore
from common.paths import NERON_ROOT
from core.runtime.governor import get_runtime_governor
from tools.models import ToolResult, ToolSpec


TOOL_SLUG = "dashboard_guardian_tool"
AGENT_SLUG = "dashboard_guardian_agent"
DASHBOARD_DIR = NERON_ROOT / "client" / "dashboard"
SRC_DIR = DASHBOARD_DIR / "src"
CONSOLE_FILE = SRC_DIR / "NeronConsole.tsx"
NERONFACE_CHUNK_RE = re.compile(r"neronface", re.IGNORECASE)


def tool_spec() -> ToolSpec:
    return ToolSpec(
        name="Dashboard Guardian Diagnostics",
        slug=TOOL_SLUG,
        description=(
            "Execute les diagnostics gouvernes du Dashboard React/Vite et "
            "retourne un rapport sans remediation automatique."
        ),
        inputs={"request": "str"},
        outputs={"report": "dict"},
        safety={
            "filesystem": "source_read_only",
            "commands": "runtime_governor_authorized",
            "remediation": "proposals_only",
        },
        source="builtin",
        metadata={"handler_path": str(Path(__file__).resolve())},
    )


def execute(payload: dict[str, Any] | None = None) -> ToolResult:
    guardian = DashboardGuardianDiagnostics()
    report = guardian.run()
    status = "healthy" if not report["summary"]["problem_count"] else "attention"
    return ToolResult(
        ok=True,
        response=f"DashboardGuardian: {status}, {report['summary']['problem_count']} probleme(s).",
        data={"report": report},
    )


class DashboardGuardianDiagnostics:
    def run(self) -> dict[str, Any]:
        report = {
            "agent": AGENT_SLUG,
            "title": "DashboardGuardian",
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "dashboard_dir": str(DASHBOARD_DIR),
            "domains": {
                "code_health": self._code_health(),
                "maintenance": self._maintenance(),
                "performance": self._performance(),
                "tests": self._tests(),
            },
            "remediation": [],
            "safety": {
                "auto_fix": False,
                "writes_source_files": False,
                "commits": False,
                "remediation_mode": "proposals_only",
            },
        }
        report["remediation"] = self._remediation(report["domains"])
        report["summary"] = self._summary(report["domains"])
        return report

    def _code_health(self) -> dict[str, Any]:
        tsc = self._run_command(
            ["pnpm", "exec", "tsc", "--noEmit"],
            timeout=120,
            reason="dashboard typescript diagnostic read",
        )
        static_checks = self._static_dashboard_checks()
        issues = []
        if tsc["returncode"] != 0:
            issues.append({
                "kind": "typescript_errors",
                "message": "tsc --noEmit a retourne des erreurs.",
                "details": self._tail(tsc["output"], 12000),
            })
        issues.extend(static_checks["issues"])
        return {
            "ok": not issues,
            "command": tsc,
            "static_checks": static_checks,
            "issues": issues,
        }

    def _maintenance(self) -> dict[str, Any]:
        outdated = self._run_command(
            ["pnpm", "outdated", "--json"],
            timeout=90,
            reason="dashboard dependency outdated diagnostic read",
        )
        audit = self._run_command(
            ["pnpm", "audit", "--json"],
            timeout=120,
            reason="dashboard dependency audit diagnostic read",
        )
        packages = self._parse_outdated(outdated["output"])
        vulnerabilities = self._parse_audit(audit["output"])
        return {
            "ok": not packages and not vulnerabilities,
            "outdated_command": outdated,
            "audit_command": audit,
            "outdated_packages": packages,
            "vulnerabilities": vulnerabilities,
        }

    def _performance(self) -> dict[str, Any]:
        build = self._run_command(
            ["pnpm", "build"],
            timeout=240,
            reason="dashboard vite build chunk diagnostic",
        )
        chunks = self._parse_chunks(build["output"])
        previous = self._previous_chunks()
        issues = self._chunk_issues(chunks, previous)
        if build["returncode"] != 0:
            issues.insert(0, {
                "kind": "build_failed",
                "message": "pnpm build a echoue.",
                "details": self._tail(build["output"], 12000),
            })
        return {
            "ok": build["returncode"] == 0 and not issues,
            "command": build,
            "chunks": chunks,
            "previous_chunks": previous,
            "issues": issues,
            "ignored_known_case": "NeronFace three.js/VRM chunk deja investigue et clos",
        }

    def _tests(self) -> dict[str, Any]:
        detected = self._detect_tests()
        if not detected["has_tests"]:
            return {
                "ok": True,
                "has_tests": False,
                "message": "aucun test detecte",
                "detected": detected,
                "command": None,
            }
        command = self._run_command(
            ["pnpm", "test"],
            timeout=180,
            reason="dashboard existing test suite diagnostic read",
        )
        return {
            "ok": command["returncode"] == 0,
            "has_tests": True,
            "message": "suite de tests detectee et executee",
            "detected": detected,
            "command": command,
        }

    def _run_command(
        self,
        command: list[str],
        *,
        timeout: int,
        reason: str,
    ) -> dict[str, Any]:
        governor = get_runtime_governor()
        allowed = governor.authorize_system_command(
            actor="dashboard_guardian",
            command=command,
            reason=reason,
        )
        if not allowed:
            return {
                "command": command,
                "cwd": str(DASHBOARD_DIR),
                "authorized": False,
                "returncode": None,
                "output": "Commande bloquee par RuntimeGovernor.",
            }
        try:
            completed = subprocess.run(
                command,
                cwd=DASHBOARD_DIR,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            output = "\n".join(
                part for part in [str(exc.stdout or ""), str(exc.stderr or "")]
                if part
            )
            return {
                "command": command,
                "cwd": str(DASHBOARD_DIR),
                "authorized": True,
                "returncode": None,
                "timed_out": True,
                "output": self._tail(output, 12000),
            }
        output = "\n".join(
            part.strip()
            for part in [completed.stdout, completed.stderr]
            if part and part.strip()
        )
        return {
            "command": command,
            "cwd": str(DASHBOARD_DIR),
            "authorized": True,
            "returncode": completed.returncode,
            "timed_out": False,
            "output": self._tail(output, 20000),
        }

    def _static_dashboard_checks(self) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        if not SRC_DIR.is_dir():
            return {"issues": [{"kind": "src_missing", "message": str(SRC_DIR)}]}
        files = sorted(SRC_DIR.rglob("*.ts")) + sorted(SRC_DIR.rglob("*.tsx"))
        exports = self._find_exports(files)
        unused_exports = [
            item for item in exports
            if not self._name_used_elsewhere(item["name"], item["file"], files)
        ]
        if unused_exports:
            issues.append({
                "kind": "unused_exports",
                "message": "Exports non importes ou non references ailleurs.",
                "items": unused_exports[:50],
                "count": len(unused_exports),
            })
        use_state = self._unused_use_state(files)
        if use_state:
            issues.append({
                "kind": "unused_use_state_values",
                "message": "Valeurs useState declarees mais jamais lues dans leur fichier.",
                "items": use_state[:50],
                "count": len(use_state),
            })
        nav_duplicates = self._nav_duplicates()
        if nav_duplicates:
            issues.append({
                "kind": "nav_duplicates",
                "message": "Doublons detectes dans le tableau nav de NeronConsole.tsx.",
                "items": nav_duplicates,
            })
        record_issues = self._window_record_issues()
        issues.extend(record_issues)
        return {"issues": issues}

    def _find_exports(self, files: list[Path]) -> list[dict[str, str]]:
        pattern = re.compile(
            r"^\s*export\s+(?:async\s+)?(?:function|class|const|let|var|type|interface)\s+([A-Za-z_]\w*)",
            re.MULTILINE,
        )
        exports: list[dict[str, str]] = []
        for file in files:
            text = self._read(file)
            for match in pattern.finditer(text):
                exports.append({"name": match.group(1), "file": str(file.relative_to(DASHBOARD_DIR))})
        return exports

    def _name_used_elsewhere(self, name: str, source_file: str, files: list[Path]) -> bool:
        token = re.compile(rf"\b{re.escape(name)}\b")
        source_path = DASHBOARD_DIR / source_file
        for file in files:
            if file == source_path:
                continue
            if token.search(self._read(file)):
                return True
        return False

    def _unused_use_state(self, files: list[Path]) -> list[dict[str, str]]:
        pattern = re.compile(
            r"const\s+\[\s*([A-Za-z_]\w*)\s*,\s*[A-Za-z_]\w*\s*\]\s*=\s*useState\b"
        )
        unused: list[dict[str, str]] = []
        for file in files:
            text = self._read(file)
            for match in pattern.finditer(text):
                name = match.group(1)
                if len(re.findall(rf"\b{re.escape(name)}\b", text)) <= 1:
                    unused.append({"name": name, "file": str(file.relative_to(DASHBOARD_DIR))})
        return unused

    def _nav_duplicates(self) -> list[dict[str, Any]]:
        text = self._read(CONSOLE_FILE)
        block = self._extract_const_object_or_array(text, "nav")
        duplicates: list[dict[str, Any]] = []
        for field in ("id", "target"):
            values = re.findall(rf"{field}:\s*'([^']+)'", block)
            for value in sorted({item for item in values if values.count(item) > 1}):
                duplicates.append({"field": field, "value": value, "count": values.count(value)})
        return duplicates

    def _window_record_issues(self) -> list[dict[str, Any]]:
        text = self._read(CONSOLE_FILE)
        ids_match = re.search(r"type\s+WindowId\s*=\s*([^;]+);", text, re.DOTALL)
        if not ids_match:
            return [{"kind": "window_id_missing", "message": "Type WindowId introuvable."}]
        ids = re.findall(r"'([^']+)'", ids_match.group(1))
        expected = set(ids)
        issues: list[dict[str, Any]] = []
        record_pattern = re.compile(
            r"const\s+([A-Za-z_]\w*)\s*:\s*Record<WindowId,[^=]+>\s*=\s*({)",
            re.MULTILINE,
        )
        for match in record_pattern.finditer(text):
            name = match.group(1)
            block = self._balanced_from(text, match.start(2), "{", "}")
            keys = set(re.findall(r"^\s*([A-Za-z_]\w*)\s*:", block, re.MULTILINE))
            keys.update(re.findall(r"^\s*'([^']+)'\s*:", block, re.MULTILINE))
            missing = sorted(expected - keys)
            extra = sorted(keys - expected)
            if missing or extra:
                issues.append({
                    "kind": "window_record_mismatch",
                    "record": name,
                    "missing": missing,
                    "extra": extra,
                    "message": f"Record<WindowId,...> incomplet: {name}",
                })
        return issues

    def _parse_outdated(self, output: str) -> list[dict[str, Any]]:
        try:
            payload = json.loads(output or "{}")
        except json.JSONDecodeError:
            return []
        if isinstance(payload, dict):
            return [
                {"name": name, **dict(info)}
                for name, info in payload.items()
                if isinstance(info, dict)
            ]
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, dict)]
        return []

    def _parse_audit(self, output: str) -> list[dict[str, Any]]:
        try:
            payload = json.loads(output or "{}")
        except json.JSONDecodeError:
            return []
        advisories = payload.get("advisories")
        if isinstance(advisories, dict):
            return [dict(item) for item in advisories.values() if isinstance(item, dict)]
        vulnerabilities = payload.get("vulnerabilities")
        if isinstance(vulnerabilities, dict):
            return [
                {"name": name, **dict(item)}
                for name, item in vulnerabilities.items()
                if isinstance(item, dict)
            ]
        return []

    def _parse_chunks(self, output: str) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        pattern = re.compile(
            r"(?:dist/)?assets/([^\s]+?\.(?:js|css))\s+([0-9.]+)\s+kB",
            re.IGNORECASE,
        )
        for name, size in pattern.findall(output or ""):
            size_kb = float(size)
            chunks.append({
                "name": name,
                "normalized_name": self._normalize_chunk_name(name),
                "size_kb": size_kb,
                "ignored": bool(NERONFACE_CHUNK_RE.search(name)),
            })
        return chunks

    def _chunk_issues(
        self,
        chunks: list[dict[str, Any]],
        previous: dict[str, float],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for chunk in chunks:
            if chunk.get("ignored"):
                continue
            size = float(chunk["size_kb"])
            name = str(chunk["normalized_name"])
            if size > 500:
                issues.append({
                    "kind": "large_chunk",
                    "chunk": chunk["name"],
                    "size_kb": size,
                    "message": "Chunk anormalement gros hors cas NeronFace.",
                })
            previous_size = previous.get(name)
            if previous_size and size - previous_size > max(50, previous_size * 0.2):
                issues.append({
                    "kind": "chunk_regression",
                    "chunk": chunk["name"],
                    "previous_kb": previous_size,
                    "size_kb": size,
                    "message": "Regression de taille de chunk depuis le build precedent.",
                })
        return issues

    def _previous_chunks(self) -> dict[str, float]:
        try:
            executions = AgentRuntimeStore().list_executions(limit=100)
        except Exception:
            return {}
        for execution in executions:
            if execution.get("agent_slug") != AGENT_SLUG or execution.get("status") != "completed":
                continue
            result = execution.get("result") or {}
            report = result.get("report") if isinstance(result, dict) else None
            domains = report.get("domains") if isinstance(report, dict) else None
            performance = domains.get("performance") if isinstance(domains, dict) else None
            chunks = performance.get("chunks") if isinstance(performance, dict) else None
            if isinstance(chunks, list):
                return {
                    str(item.get("normalized_name") or item.get("name")): float(item.get("size_kb") or 0)
                    for item in chunks
                    if isinstance(item, dict)
                }
        return {}

    def _detect_tests(self) -> dict[str, Any]:
        package = self._package_json()
        scripts = dict(package.get("scripts") or {}) if isinstance(package, dict) else {}
        test_script = str(scripts.get("test") or "")
        test_files = [
            str(path.relative_to(DASHBOARD_DIR))
            for pattern in ("*.test.*", "*.spec.*")
            for path in SRC_DIR.rglob(pattern)
        ] if SRC_DIR.is_dir() else []
        has_tests = bool(test_script and test_script.lower() not in {"echo \"error: no test specified\" && exit 1"})
        has_tests = has_tests or bool(test_files)
        return {"has_tests": has_tests, "test_script": test_script or None, "test_files": sorted(test_files)[:50]}

    def _package_json(self) -> dict[str, Any]:
        try:
            return json.loads((DASHBOARD_DIR / "package.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _remediation(self, domains: dict[str, Any]) -> list[str]:
        proposals: list[str] = []
        code = domains.get("code_health", {})
        if not code.get("ok"):
            proposals.append("Corriger les erreurs TypeScript et nettoyer les exports/useState signales avant toute evolution du Dashboard.")
        maintenance = domains.get("maintenance", {})
        if maintenance.get("outdated_packages"):
            proposals.append("Preparer une mise a jour controlee des dependances obsoletees, avec validation humaine du diff pnpm-lock.")
        if maintenance.get("vulnerabilities"):
            proposals.append("Examiner les vulnerabilites pnpm audit et proposer un plan de mise a jour dedie.")
        performance = domains.get("performance", {})
        if performance.get("issues"):
            proposals.append("Analyser les chunks signales hors NeronFace et envisager lazy-loading ou split de dependance apres validation.")
        tests = domains.get("tests", {})
        if not tests.get("has_tests"):
            proposals.append("Aucun test detecte: ouvrir un chantier separe pour definir la suite de tests Dashboard.")
        elif not tests.get("ok"):
            proposals.append("Corriger la suite de tests existante avant de livrer de nouvelles modifications frontend.")
        if not proposals:
            proposals.append("Aucune remediation immediate proposee.")
        return proposals

    def _summary(self, domains: dict[str, Any]) -> dict[str, Any]:
        problem_count = 0
        for value in domains.values():
            if isinstance(value, dict) and not value.get("ok", True):
                problem_count += 1
        return {
            "status": "healthy" if problem_count == 0 else "attention",
            "problem_count": problem_count,
            "domains_ok": {
                name: bool(value.get("ok"))
                for name, value in domains.items()
                if isinstance(value, dict)
            },
        }

    @staticmethod
    def _normalize_chunk_name(name: str) -> str:
        return re.sub(r"-[A-Za-z0-9_-]{8,}(?=\.)", "", name)

    @staticmethod
    def _read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    @staticmethod
    def _tail(text: str, limit: int) -> str:
        return (text or "")[-limit:]

    def _extract_const_object_or_array(self, text: str, name: str) -> str:
        match = re.search(rf"const\s+{re.escape(name)}\b[^=]*=\s*([\[{{])", text)
        if not match:
            return ""
        opener = match.group(1)
        closer = "]" if opener == "[" else "}"
        return self._balanced_from(text, match.start(1), opener, closer)

    @staticmethod
    def _balanced_from(text: str, start: int, opener: str, closer: str) -> str:
        depth = 0
        quote: str | None = None
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in {"'", '"', "`"}:
                quote = char
                continue
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]
        return text[start:]
