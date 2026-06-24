from __future__ import annotations

import importlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from goal.goals.goal_manager import get_goal_manager
from goal.planning import AutonomousPlanner
from goal.planning.storage import PlanStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | neron.cognitive_loop | %(message)s",
)

logger = logging.getLogger("neron.cognitive_loop")

ACTION_HISTORY_PATH = Path("/etc/neron/data/action_history.jsonl")


def _json_default(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()

    if hasattr(value, "__dict__"):
        return value.__dict__

    return str(value)


def _save_action(payload: dict[str, Any]) -> None:
    ACTION_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    with ACTION_HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=_json_default) + "\n")


def _read_active_goal() -> str | None:
    goal = get_goal_manager().get_active_goal()
    return str(goal.get("title")) if goal else None


def _recent_plan_exists(goal: str, cooldown_seconds: int = 3600) -> bool:
    storage = PlanStorage()
    now = datetime.now(timezone.utc)

    for plan in storage.history(limit=30):
        if plan.get("source") != "cognitive_loop":
            continue

        if plan.get("goal") != goal:
            continue

        created_at = plan.get("created_at")
        if not created_at:
            return True

        try:
            created = datetime.fromisoformat(created_at)
        except Exception:
            return True

        age = (now - created).total_seconds()
        if age < cooldown_seconds:
            return True

    return False


def _generate_plan_from_goal() -> dict[str, Any]:
    goal = _read_active_goal()

    if not goal:
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "generate_task_plan",
            "target": "planner",
            "priority": "medium",
            "status": "blocked",
            "message": "Aucun objectif actif disponible.",
        }
        _save_action(result)
        return result

    if _recent_plan_exists(goal):
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "generate_task_plan",
            "target": "planner",
            "priority": "low",
            "status": "skipped",
            "message": "Plan récent déjà existant pour cet objectif.",
            "active_goal": goal,
        }
        _save_action(result)
        return result

    planner = AutonomousPlanner()
    storage = PlanStorage()

    plan = planner.create_plan(goal)
    data = plan.to_dict()
    data["approved"] = False
    data["approval_required"] = True
    data["source"] = "cognitive_loop"
    active = get_goal_manager().get_active_goal()
    data["goal_id"] = active.get("id") if active else None

    storage.save(data)

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "generate_task_plan",
        "target": "planner",
        "priority": "medium",
        "status": "success",
        "message": "Plan généré automatiquement depuis la Cognitive Loop.",
        "generated_plan_id": data.get("id"),
        "generated_plan_goal": data.get("goal"),
    }

    _save_action(result)
    return result


def _run_cognitive_core_once() -> dict[str, Any] | None:
    try:
        module = importlib.import_module("modules.cognitive_core.core")
    except Exception as exc:
        logger.warning("Cognitive Core indisponible: %s", exc)
        return None

    core = None

    if hasattr(module, "get_cognitive_core"):
        try:
            core = module.get_cognitive_core()
        except Exception as exc:
            logger.warning("get_cognitive_core erreur: %s", exc)
            core = None

    if core is None and hasattr(module, "CognitiveCore"):
        try:
            core = module.CognitiveCore()
        except Exception as exc:
            logger.warning("CognitiveCore instanciation erreur: %s", exc)
            core = None

    if core is None:
        return None

    for method_name in ["cycle", "run_cycle", "evaluate", "tick", "step"]:
        method = getattr(core, method_name, None)

        if method is None:
            continue

        try:
            state = method()

            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "cognitive_core_cycle",
                "target": "cognitive_core",
                "priority": "medium",
                "status": "success",
                "message": f"Cognitive Core exécuté via {method_name}.",
                "state": _json_default(state),
            }

            _save_action(result)
            return result

        except Exception as exc:
            logger.warning("Cognitive Core méthode %s erreur: %s", method_name, exc)

    return None


def main() -> None:
    logger.info("CognitiveLoop démarrée")

    while True:
        logger.info("[CognitiveLoop] cycle actif")

        result = _run_cognitive_core_once()

        if result is None:
            result = _generate_plan_from_goal()

        logger.info(
            "[CognitiveLoop] result status=%s action=%s",
            result.get("status"),
            result.get("action"),
        )

        time.sleep(10)


if __name__ == "__main__":
    main()
