from __future__ import annotations

import os
from pathlib import Path

from agents.factory.agent_creator import DEFAULT_PROPOSALS_PATH
from agents.factory.registry import DEFAULT_GENERATED_AGENTS
from core.modules.self_model.service import STATE_PATH
from core.storage.sqlite_store import DEFAULT_DATABASE_PATH
from goal.goals.persistence import GOALS_PATH
from goal.planning.storage import DEFAULT_PLAN_HISTORY_PATH
from goal.projects.manager import PROJECTS_PATH
from goal.system.task_manager import TASKS_FILE
from modules.cognitive.action_executor import ACTION_HISTORY_PATH
from modules.cognitive.critic_engine import CRITIC_HISTORY_PATH
from modules.evolution.storage import EVOLUTION_STATE_PATH
from modules.world_model.world_model import WORLD_STATE_PATH


def test_persistent_test_paths_are_isolated_from_production():
    test_root = Path(os.environ["NERON_TEST_ROOT"]).resolve()
    paths = (
        DEFAULT_PROPOSALS_PATH,
        DEFAULT_GENERATED_AGENTS,
        STATE_PATH,
        DEFAULT_DATABASE_PATH,
        GOALS_PATH,
        DEFAULT_PLAN_HISTORY_PATH,
        PROJECTS_PATH,
        TASKS_FILE,
        ACTION_HISTORY_PATH,
        CRITIC_HISTORY_PATH,
        EVOLUTION_STATE_PATH,
        WORLD_STATE_PATH,
    )

    for path in paths:
        Path(path).resolve().relative_to(test_root)
