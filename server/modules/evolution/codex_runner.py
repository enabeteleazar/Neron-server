from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from common.paths import NERON_ROOT
from modules.evolution.models import CommandResult

CODEX_MISSING_ERROR = "Codex CLI introuvable. Configure NERON_CODEX_BIN ou PATH systemd."
CODEX_PREFLIGHT_ERROR = "Pré-vol Codex échoué: codex exec --help a échoué."
CODEX_PROBE_TIMEOUT_SECONDS = 10
KNOWN_CODEX_PATHS = (
    Path("/home/neron/.local/bin/codex"),
    Path("/usr/local/bin/codex"),
    Path("/usr/bin/codex"),
)
APPROVAL_OPTION_CANDIDATES = ("--ask-for-approval", "--approval-mode", "--approval-policy")
SANDBOX_OPTION_CANDIDATES = ("--sandbox", "--sandbox-mode")


SECRET_PATTERNS = [
    (
        re.compile(r"(?i)(api[_-]?key|token|secret|password)(\s*[=:]\s*)([^\s]+)"),
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
    ),
    (
        re.compile(r"(?i)(bearer\s+)[a-z0-9._\-]+"),
        lambda match: f"{match.group(1)}[REDACTED]",
    ),
    (
        re.compile(r"(?i)(x-api-key\s*[:=]\s*)[^\s]+"),
        lambda match: f"{match.group(1)}[REDACTED]",
    ),
]


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def resolve_codex_bin() -> tuple[str | None, str | None]:
    configured = os.getenv("NERON_CODEX_BIN", "").strip()
    if configured:
        configured_path = Path(configured)
        if configured_path.is_file() and os.access(configured_path, os.X_OK):
            return str(configured_path), None
        return None, CODEX_MISSING_ERROR

    path_match = shutil.which("codex")
    if path_match:
        return path_match, None

    for known_path in KNOWN_CODEX_PATHS:
        if known_path.is_file() and os.access(known_path, os.X_OK):
            return str(known_path), None

    return None, CODEX_MISSING_ERROR


def extract_codex_exec_options(help_text: str) -> list[str]:
    options = set()
    for line in help_text.splitlines():
        match = re.match(r"^\s*(?:-[A-Za-z0-9],\s*)?(--[a-z0-9][a-z0-9-]*)\b", line)
        if match:
            options.add(match.group(1))
    return sorted(options)


def build_codex_exec_command(codex_bin: str, help_text: str, prompt: str) -> list[str]:
    supported_options = set(extract_codex_exec_options(help_text))
    command = [codex_bin, "exec"]

    approval_option = _first_supported_option(supported_options, APPROVAL_OPTION_CANDIDATES)
    if approval_option:
        command.extend([approval_option, "never"])

    sandbox_option = _first_supported_option(supported_options, SANDBOX_OPTION_CANDIDATES)
    if sandbox_option:
        command.extend([sandbox_option, "workspace-write"])

    command.append(prompt)
    return command


def probe_codex_cli(codex_bin: str) -> dict[str, str | list[str] | None]:
    version = _run_probe([codex_bin, "--version"])
    help_result = _run_probe([codex_bin, "exec", "--help"])
    help_text = help_result["output"] if help_result["ok"] else ""
    error = None if help_result["ok"] else CODEX_PREFLIGHT_ERROR
    return {
        "codex_version": version["output"] if version["ok"] else None,
        "codex_exec_supported_options": extract_codex_exec_options(help_text),
        "codex_error": error,
    }


def _first_supported_option(supported_options: set[str], candidates: tuple[str, ...]) -> str | None:
    for option in candidates:
        if option in supported_options:
            return option
    return None


def _run_probe(command: list[str]) -> dict[str, str | bool]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=CODEX_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception as exc:
        return {"ok": False, "output": redact_secrets(str(exc))}
    output = redact_secrets((completed.stdout or completed.stderr or "").strip())
    return {"ok": completed.returncode == 0, "output": output}


class CodexRunner:
    def __init__(
        self,
        *,
        workspace: Path = NERON_ROOT,
        timeout_seconds: int | None = None,
        dry_run: bool | None = None,
    ) -> None:
        self.workspace = workspace
        self.timeout_seconds = timeout_seconds or int(os.getenv("NERON_CODEX_TIMEOUT", "1800"))
        self.dry_run = bool(dry_run) if dry_run is not None else os.getenv("NERON_CODEX_DRY_RUN") == "1"
        self._process: asyncio.subprocess.Process | None = None

    def codex_status(self) -> dict[str, str | bool | list[str] | None]:
        codex_bin, error = resolve_codex_bin()
        probe = (
            probe_codex_cli(codex_bin)
            if codex_bin
            else {"codex_version": None, "codex_exec_supported_options": [], "codex_error": error}
        )
        probe_error = probe.get("codex_error")
        return {
            "codex_available": codex_bin is not None and probe_error is None,
            "codex_bin": codex_bin,
            "codex_error": error or probe_error,
            "codex_version": probe.get("codex_version"),
            "codex_exec_supported_options": probe.get("codex_exec_supported_options") or [],
        }

    async def run_codex(self, prompt: str, run_id: str) -> CommandResult:
        if self.dry_run:
            return CommandResult(
                name="codex",
                command=["codex", "dry-run"],
                returncode=0,
                stdout=f"Dry-run Codex execution for {run_id}. Prompt length: {len(prompt)}",
            )

        codex_bin, error = resolve_codex_bin()
        if not codex_bin:
            return CommandResult(
                name="codex",
                command=["codex", "exec"],
                returncode=1,
                stderr=error or CODEX_MISSING_ERROR,
            )

        preflight = await self.run_command(
            "codex_exec_help",
            [codex_bin, "exec", "--help"],
            timeout=CODEX_PROBE_TIMEOUT_SECONDS,
        )
        if not preflight.ok:
            return CommandResult(
                name="codex",
                command=[codex_bin, "exec"],
                returncode=1,
                stderr=preflight.stderr or preflight.stdout or CODEX_PREFLIGHT_ERROR,
            )

        command = build_codex_exec_command(codex_bin, preflight.stdout + preflight.stderr, prompt)
        return await self.run_command("codex", command, timeout=self.timeout_seconds)

    async def run_tests(self) -> list[CommandResult]:
        commands = [
            ("compileall", [sys.executable, "-m", "compileall", "core"]),
            (
                "tracked_agent_workflow",
                [sys.executable, "-m", "pytest", "tests/test_tracked_agent_workflow.py", "-v"],
            ),
            ("parallel", [sys.executable, "-m", "pytest", "tests/test_parallel.py", "-v"]),
            ("pytest", [sys.executable, "-m", "pytest", "-q"]),
            ("git_diff_check", ["git", "diff", "--check"]),
        ]
        results: list[CommandResult] = []
        for name, command in commands:
            result = await self.run_command(name, command, timeout=self.timeout_seconds)
            results.append(result)
            if not result.ok:
                break
        return results

    async def commit_and_push(self, message: str) -> dict:
        status = await self.run_command("git_status", ["git", "status", "--short"], timeout=60)
        add = await self.run_command("git_add", ["git", "add", "."], timeout=120)
        if not add.ok:
            return {"ok": False, "status": status.to_dict(), "add": add.to_dict(), "pushed": False}

        commit = await self.run_command("git_commit", ["git", "commit", "-m", message], timeout=180)
        if not commit.ok:
            return {
                "ok": False,
                "status": status.to_dict(),
                "add": add.to_dict(),
                "commit": commit.to_dict(),
                "pushed": False,
            }

        branch = await self.run_command("git_branch", ["git", "branch", "--show-current"], timeout=30)
        commit_hash = await self.run_command("git_rev_parse", ["git", "rev-parse", "HEAD"], timeout=30)
        push = await self.run_command("git_push", ["git", "push", "origin", "HEAD"], timeout=600)
        return {
            "ok": push.ok,
            "status": status.to_dict(),
            "add": add.to_dict(),
            "commit": commit.to_dict(),
            "push": push.to_dict(),
            "pushed": push.ok,
            "branch": branch.stdout.strip() if branch.ok else None,
            "commit_hash": commit_hash.stdout.strip() if commit_hash.ok else None,
        }

    async def run_command(
        self,
        name: str,
        command: list[str],
        *,
        timeout: int | None = None,
    ) -> CommandResult:
        try:
            self._process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(self.workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                self._process.communicate(),
                timeout=timeout or self.timeout_seconds,
            )
            return CommandResult(
                name=name,
                command=command,
                returncode=int(self._process.returncode or 0),
                stdout=redact_secrets(stdout.decode("utf-8", errors="replace")),
                stderr=redact_secrets(stderr.decode("utf-8", errors="replace")),
            )
        except asyncio.TimeoutError:
            await self.cancel()
            return CommandResult(name=name, command=command, returncode=124, timed_out=True)
        except Exception as exc:
            return CommandResult(
                name=name,
                command=command,
                returncode=1,
                stderr=redact_secrets(str(exc)),
            )
        finally:
            self._process = None

    async def cancel(self) -> None:
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
