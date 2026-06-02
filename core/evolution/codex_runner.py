from __future__ import annotations

import asyncio
import os
import re
import shlex
import sys
from pathlib import Path

from core.evolution.models import CommandResult


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


class CodexRunner:
    def __init__(
        self,
        *,
        workspace: Path = Path("/etc/neron"),
        timeout_seconds: int | None = None,
        dry_run: bool | None = None,
    ) -> None:
        self.workspace = workspace
        self.timeout_seconds = timeout_seconds or int(os.getenv("NERON_CODEX_TIMEOUT", "1800"))
        self.dry_run = bool(dry_run) if dry_run is not None else os.getenv("NERON_CODEX_DRY_RUN") == "1"
        self._process: asyncio.subprocess.Process | None = None

    async def run_codex(self, prompt: str, run_id: str) -> CommandResult:
        if self.dry_run:
            return CommandResult(
                name="codex",
                command=["codex", "dry-run"],
                returncode=0,
                stdout=f"Dry-run Codex execution for {run_id}. Prompt length: {len(prompt)}",
            )

        command = shlex.split(
            os.getenv(
                "NERON_CODEX_COMMAND",
                "codex exec --ask-for-approval never --sandbox workspace-write",
            )
        )
        return await self.run_command("codex", command + [prompt], timeout=self.timeout_seconds)

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
