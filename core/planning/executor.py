from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PlanExecutor:
    def __init__(self, project_root: Path | None = None):
        if project_root is None:
            project_root = Path(os.getenv("NERON_PROJECT_ROOT", Path.cwd()))
        self.project_root = project_root
        self.draft_dir = self.project_root / "workspace" / "agent_drafts"
        self.draft_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, plan: dict[str, Any]) -> dict[str, Any]:
        if not plan.get("approved"):
            plan["status"] = "approval_required"
            plan["error"] = "Plan non approuvé."
            return plan

        plan["status"] = "running"
        plan["executed_at"] = datetime.now(timezone.utc).isoformat()

        completed = 0
        skipped = 0

        for step in plan.get("steps", []):
            step["status"] = "running"

            try:
                step["result"] = self._execute_step(step, plan)
                if step["result"].get("status") == "skipped":
                    step["status"] = "skipped"
                    skipped += 1
                else:
                    step["status"] = "completed"
                    completed += 1
                step["error"] = None
            except Exception as exc:
                step["status"] = "failed"
                step["error"] = str(exc)
                plan["status"] = "failed"
                return plan

        plan["task_counts"] = {
            "total": completed + skipped,
            "completed": completed,
            "skipped": skipped,
            "failed": 0,
        }

        if skipped and not completed:
            plan["status"] = "partial"
            plan["error"] = "Aucune étape exécutable n'a été terminée."
            return plan

        plan["status"] = "plan_finished"
        plan["error"] = None
        return plan

    def _execute_step(self, step: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        action = step.get("action")

        if action in {"analyze_agents", "check_integration", "scan_project"}:
            return self._scan_agents()

        if action in {"define_agent", "create_skeleton"}:
            return self._create_agent_draft(plan)

        if action in {"prepare_tests", "run_tests"}:
            return self._run_tests()

        if action in {"evaluate_risk", "evaluate_plan", "security_audit"}:
            return {
                "risk": "medium",
                "requires_human_review": True,
                "reason": "Modification du Core interdite en mode Executor V1.",
            }

        return {
            "status": "skipped",
            "reason": "Action non implémentée dans Executor V1.",
        }

    def _scan_agents(self) -> dict[str, Any]:
        agents_dir = self.project_root / "agents"
        files = []

        if agents_dir.exists():
            files = sorted(
                str(path.relative_to(self.project_root))
                for path in agents_dir.rglob("*.py")
            )

        return {
            "agents_dir": str(agents_dir),
            "files_found": len(files),
            "sample": files[:20],
        }

    def _create_agent_draft(self, plan: dict[str, Any]) -> dict[str, Any]:
        goal = str(plan.get("goal") or "nouvel agent")
        goal_lower = goal.lower()

        if "météo" in goal_lower or "meteo" in goal_lower:
            safe_name = "weather_agent"
        elif "wwdc" in goal_lower:
            safe_name = "wwdc_agent"
        elif "test" in goal_lower:
            safe_name = "test_agent"
        else:
            safe_name = self._agent_name_from_goal(goal)

        class_name = self._class_name_from_safe_name(safe_name)

        agent_file = self.draft_dir / (safe_name + ".py")

        lines = [
            "from __future__ import annotations",
            "",
            "",
            "class " + class_name + ":",
            "    name = " + repr(safe_name),
            "",
            "    def __init__(self):",
            "        self.goal = " + repr(goal),
            "",
            "    async def run(self, action: str | None = None, params: dict | None = None) -> dict:",
            "        return {",
            "            'agent': self.name,",
            "            'action': action,",
            "            'params': params or {},",
            "            'status': 'draft_only',",
            "            'goal': self.goal,",
            "        }",
            "",
        ]

        agent_file.write_text("\n".join(lines), encoding="utf-8")

        return {
            "draft_created": True,
            "path": str(agent_file),
            "agent_path": str(agent_file),
            "draft_only": True,
            "state": "draft_only",
            "applied_to_core": False,
        }

    def _agent_name_from_goal(self, goal: str) -> str:
        normalized = goal.lower()
        for token in ("créer", "creer", "agent", "qui", "me", "de", "la", "le", "un", "une", "des", "du", "prochaine", "prochain"):
            normalized = normalized.replace(token, " ")

        words = re.findall(r"[a-z0-9]+", normalized)
        selected = words[:3] or ["generated"]
        return "_".join(selected) + "_agent"

    def _class_name_from_safe_name(self, safe_name: str) -> str:
        return "".join(part.capitalize() for part in safe_name.split("_") if part)

    def _run_tests(self) -> dict[str, Any]:
        result = subprocess.run(
            ["python3", "-m", "pytest", "-q"],
            cwd=self.project_root,
            text=True,
            capture_output=True,
            timeout=120,
        )

        return {
            "command": "python3 -m pytest -q",
            "returncode": result.returncode,
            "success": result.returncode == 0,
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
        }
