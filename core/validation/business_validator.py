from __future__ import annotations

import json
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any


_RESULT_MARKER = "__NERON_BUSINESS_VALIDATION_RESULT__"
_GENERIC_RESPONSE_MARKERS = (
    "agent disponible pour",
    "je suis un agent",
    "reponse deterministe",
)

_ISOLATED_RUNNER = r"""
import asyncio
import importlib.util
import inspect
import json
import pathlib
import sys
import traceback

marker, agent_path, prompt, project_root = sys.argv[1:5]
sys.path.insert(0, project_root)

async def main():
    module_spec = importlib.util.spec_from_file_location(
        "neron_business_validation_agent",
        pathlib.Path(agent_path),
    )
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("agent_import_spec_unavailable")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    agent = module.Agent()
    execute = agent.execute
    parameters = inspect.signature(execute).parameters
    if "text" in parameters:
        result = execute(text=prompt)
    elif "query" in parameters:
        result = execute(query=prompt)
    elif parameters:
        first = next(iter(parameters.values()))
        if first.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            result = execute(prompt)
        else:
            result = execute()
    else:
        result = execute()
    if inspect.isawaitable(result):
        result = await result
    print(marker + json.dumps({"ok": True, "result": result}, default=str))

try:
    asyncio.run(main())
except Exception as exc:
    print(
        marker
        + json.dumps(
            {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=5),
            }
        )
    )
"""


class BusinessValidator:
    def __init__(
        self,
        *,
        python_executable: str | None = None,
        project_root: Path | None = None,
        timeout: int = 30,
    ) -> None:
        self.python_executable = python_executable or sys.executable
        self.project_root = (project_root or Path("/etc/neron")).resolve()
        self.timeout = timeout

    def validate(
        self,
        agent_spec: dict[str, Any] | Any,
        agent_path: str | Path,
        original_goal: str,
        scenario: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        spec = self._spec_dict(agent_spec)
        selected_scenario = scenario or self.generate_scenario(spec, original_goal)
        expected = dict(selected_scenario.get("expected") or {})
        result = {
            "ok": False,
            "status": "failed",
            "scenario": selected_scenario,
            "actual_response": "",
            "expected": expected,
            "errors": [],
        }

        path = Path(agent_path).resolve()
        if not path.is_file():
            result["errors"].append(f"agent_file_not_found: {path}")
            return result

        execution = self._execute_agent(path, str(selected_scenario.get("input") or original_goal))
        if not execution.get("ok"):
            result["errors"].append(str(execution.get("error") or "agent_execution_failed"))
            return result

        raw = execution.get("result")
        response = self._response_text(raw)
        result["actual_response"] = response
        result["errors"].extend(self._evaluate(raw, response, expected))
        if not result["errors"]:
            result["ok"] = True
            result["status"] = "passed"
        return result

    def generate_scenario(
        self,
        agent_spec: dict[str, Any] | Any,
        original_goal: str,
    ) -> dict[str, Any]:
        spec = self._spec_dict(agent_spec)
        searchable = self._normalize(
            " ".join(
                [
                    original_goal,
                    str(spec.get("goal") or ""),
                    str(spec.get("name") or ""),
                    " ".join(str(item) for item in spec.get("capabilities") or []),
                ]
            )
        )

        if "paques" in searchable or "easter" in searchable:
            return {
                "name": "easter_2027",
                "input": "Quelle est la date de Pâques en 2027 ?",
                "expected": {
                    "contains_all": ["2027"],
                    "contains_any": ["28 mars", "2027-03-28"],
                },
                "fallback": False,
            }
        if "noel" in searchable or "christmas" in searchable:
            return {
                "name": "christmas_countdown",
                "input": "Combien de temps reste-t-il avant Noël ?",
                "expected": {
                    "contains_any": ["Noël", "25/12"],
                },
                "fallback": False,
            }
        if (
            "subnet" in searchable
            or "ipv4" in searchable
            or "reseau ip" in searchable
        ):
            return {
                "name": "ipv4_subnet",
                "input": "Calcule le réseau de 192.168.1.42/24",
                "expected": {
                    "contains_any": ["192.168.1.0", "réseau"],
                },
                "fallback": False,
            }
        return {
            "name": "generic_non_empty_response",
            "input": original_goal,
            "expected": {
                "non_empty": True,
                "reject_generic_markers": list(_GENERIC_RESPONSE_MARKERS),
            },
            "fallback": True,
        }

    def _execute_agent(self, agent_path: Path, prompt: str) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                [
                    self.python_executable,
                    "-I",
                    "-c",
                    _ISOLATED_RUNNER,
                    _RESULT_MARKER,
                    str(agent_path),
                    prompt,
                    str(self.project_root),
                ],
                cwd=self.project_root,
                text=True,
                capture_output=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "agent_execution_timeout"}
        except Exception as exc:
            return {"ok": False, "error": f"agent_execution_error: {exc}"}

        payload_line = next(
            (
                line[len(_RESULT_MARKER) :]
                for line in reversed(completed.stdout.splitlines())
                if line.startswith(_RESULT_MARKER)
            ),
            None,
        )
        if payload_line is None:
            detail = completed.stderr.strip() or completed.stdout.strip()
            return {
                "ok": False,
                "error": f"agent_execution_no_result: {detail[-1000:]}",
            }
        try:
            payload = json.loads(payload_line)
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"agent_execution_invalid_result: {exc}"}
        if not payload.get("ok"):
            return {
                "ok": False,
                "error": str(payload.get("error") or "agent_execution_failed"),
            }
        return payload

    def _evaluate(
        self,
        raw_result: Any,
        response: str,
        expected: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []
        if isinstance(raw_result, dict):
            status = self._normalize(str(raw_result.get("status") or ""))
            if status and status not in {"ok", "success", "passed"}:
                errors.append(f"agent_status_not_ok: {raw_result.get('status')}")

        normalized_response = self._normalize(response)
        if expected.get("non_empty") and not normalized_response:
            errors.append("empty_business_response")

        missing_all = [
            value
            for value in expected.get("contains_all") or []
            if self._normalize(str(value)) not in normalized_response
        ]
        if missing_all:
            errors.append(f"missing_expected_values: {', '.join(map(str, missing_all))}")

        contains_any = list(expected.get("contains_any") or [])
        if contains_any and not any(
            self._normalize(str(value)) in normalized_response
            for value in contains_any
        ):
            errors.append(
                f"missing_any_expected_value: {', '.join(map(str, contains_any))}"
            )

        rejected = [
            marker
            for marker in expected.get("reject_generic_markers") or []
            if self._normalize(str(marker)) in normalized_response
        ]
        if rejected:
            errors.append(f"generic_response_rejected: {', '.join(map(str, rejected))}")
        return errors

    def _response_text(self, result: Any) -> str:
        if isinstance(result, dict):
            for key in ("response", "content", "result", "answer"):
                value = result.get(key)
                if value is not None:
                    return str(value).strip()
            return json.dumps(result, ensure_ascii=False, default=str)
        return str(result or "").strip()

    def _spec_dict(self, agent_spec: dict[str, Any] | Any) -> dict[str, Any]:
        if isinstance(agent_spec, dict):
            return agent_spec
        if hasattr(agent_spec, "to_dict"):
            return dict(agent_spec.to_dict())
        return {}

    def _normalize(self, value: str) -> str:
        text = unicodedata.normalize("NFKD", value.lower())
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        return " ".join(text.split())
