from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_RESULT_MARKER = "__NERON_AGENT_SANDBOX_RESULT__"


class AgentSandbox:
    def __init__(
        self,
        *,
        project_root: Path | str = Path("/etc/neron"),
        workspace: Path | str | None = None,
        python_executable: str | None = None,
        timeout: int = 30,
        memory_bytes: int = 512 * 1024 * 1024,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.workspace = Path(workspace or self.project_root / "workspace").resolve()
        self.python_executable = python_executable or sys.executable
        self.timeout = timeout
        self.memory_bytes = memory_bytes
        self._runner = Path(__file__).with_name("_runner.py").resolve()
        self._bwrap = shutil.which("bwrap")
        self._bwrap_available = self._probe_bwrap()

    def run_pytest(
        self,
        test_file: Path | str,
        *,
        timeout: int | None = None,
        name: str = "pytest_agent",
    ) -> dict[str, Any]:
        return self._run(
            {
                "mode": "pytest",
                "arguments": ["-q", str(Path(test_file).resolve())],
            },
            timeout=timeout,
            name=name,
        )

    def execute_agent(
        self,
        agent_path: Path | str,
        prompt: str,
        *,
        timeout: int | None = None,
        name: str = "agent_execution",
    ) -> dict[str, Any]:
        result = self._run(
            {
                "mode": "agent",
                "agent_path": str(Path(agent_path).resolve()),
                "prompt": prompt,
            },
            timeout=timeout,
            name=name,
        )
        payload = result.get("payload") or {}
        if result["returncode"] != 0 or not payload.get("ok"):
            return {
                "ok": False,
                "error": (
                    payload.get("error")
                    or result.get("error")
                    or result.get("stderr_tail")
                    or "agent_sandbox_failed"
                ),
                "sandbox": result,
            }
        return {
            "ok": True,
            "result": payload.get("result"),
            "sandbox": result,
        }

    def _run(
        self,
        config: dict[str, Any],
        *,
        timeout: int | None,
        name: str,
    ) -> dict[str, Any]:
        self.workspace.mkdir(parents=True, exist_ok=True)
        sandbox_tmp = self.workspace / ".sandbox_tmp"
        sandbox_tmp.mkdir(parents=True, exist_ok=True)
        effective_timeout = max(1, int(timeout or self.timeout))
        payload = {
            **config,
            "project_root": str(self.project_root),
            "workspace": str(self.workspace),
            "limits": {
                "cpu_seconds": effective_timeout + 1,
                "memory_bytes": self.memory_bytes,
                "file_bytes": 16 * 1024 * 1024,
                "open_files": 64,
                "processes": 16,
            },
        }
        command = [
            self.python_executable,
            "-I",
            str(self._runner),
            json.dumps(payload, ensure_ascii=True),
        ]
        isolation = "python_audit"
        if self._bwrap_available and self._bwrap:
            command = self._bwrap_command(command, sandbox_tmp)
            isolation = "bubblewrap"

        environment = {
            "HOME": str(self.workspace),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(sandbox_tmp),
        }
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            process = subprocess.Popen(
                command,
                cwd=self.workspace,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=effective_timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
                return {
                    "name": name,
                    "command": self._redacted_command(command),
                    "returncode": -signal.SIGKILL,
                    "stdout_tail": stdout[-4000:],
                    "stderr_tail": stderr[-4000:],
                    "error": "agent_sandbox_timeout",
                    "timed_out": True,
                    "isolation": isolation,
                    "ran_at": started_at,
                }
        except Exception as exc:
            return {
                "name": name,
                "command": self._redacted_command(command),
                "returncode": 1,
                "stdout_tail": "",
                "stderr_tail": "",
                "error": f"agent_sandbox_error: {exc}",
                "timed_out": False,
                "isolation": isolation,
                "ran_at": started_at,
            }

        result = {
            "name": name,
            "command": self._redacted_command(command),
            "returncode": process.returncode,
            "stdout_tail": stdout[-4000:],
            "stderr_tail": stderr[-4000:],
            "timed_out": False,
            "isolation": isolation,
            "ran_at": started_at,
        }
        result["payload"] = self._extract_payload(stdout)
        if "returncode" in result["payload"]:
            result["returncode"] = int(result["payload"]["returncode"])
        if not result["payload"].get("ok"):
            result["error"] = result["payload"].get("error") or "agent_sandbox_failed"
        return result

    def _probe_bwrap(self) -> bool:
        if not self._bwrap:
            return False
        try:
            completed = subprocess.run(
                [
                    self._bwrap,
                    "--die-with-parent",
                    "--new-session",
                    "--unshare-net",
                    "--ro-bind",
                    "/",
                    "/",
                    "--proc",
                    "/proc",
                    "--dev",
                    "/dev",
                    "/usr/bin/true",
                ],
                text=True,
                capture_output=True,
                timeout=3,
            )
        except Exception:
            return False
        return completed.returncode == 0

    def _bwrap_command(self, command: list[str], sandbox_tmp: Path) -> list[str]:
        return [
            str(self._bwrap),
            "--die-with-parent",
            "--new-session",
            "--unshare-net",
            "--ro-bind",
            "/",
            "/",
            "--bind",
            str(self.workspace),
            str(self.workspace),
            "--tmpfs",
            "/tmp",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--chdir",
            str(self.workspace),
            "--clearenv",
            "--setenv",
            "HOME",
            str(self.workspace),
            "--setenv",
            "PATH",
            "/usr/local/bin:/usr/bin:/bin",
            "--setenv",
            "TMPDIR",
            str(sandbox_tmp),
            *command,
        ]

    def _extract_payload(self, stdout: str) -> dict[str, Any]:
        line = next(
            (
                item[len(_RESULT_MARKER) :]
                for item in reversed(stdout.splitlines())
                if item.startswith(_RESULT_MARKER)
            ),
            None,
        )
        if line is None:
            return {"ok": False, "error": "agent_sandbox_no_result"}
        try:
            return dict(json.loads(line))
        except (TypeError, ValueError) as exc:
            return {"ok": False, "error": f"agent_sandbox_invalid_result: {exc}"}

    def _redacted_command(self, command: list[str]) -> list[str]:
        redacted = list(command)
        if redacted:
            redacted[-1] = "[SANDBOX_CONFIG]"
        return redacted
