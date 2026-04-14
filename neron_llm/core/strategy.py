"""Strategy layer — decides execution mode automatically based on task.

The strategy engine determines whether to use single, parallel, or race
mode when the caller does not specify one explicitly.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("neron_llm.strategy")

# Task → mode mapping. Override via neron.yaml if needed.
TASK_STRATEGIES: dict[str, str] = {
    "code": "parallel",
    "chat": "race",
    "fast": "single",
    "summary": "single",
    "default": "single",
}


class StrategyEngine:
    """Decides execution mode based on task type or explicit override."""

    def decide(self, task: str | None = None, mode: str | None = None) -> str:
        """Return the execution mode.

        Priority: explicit mode > task-based strategy > 'single'.
        """
        if mode:
            logger.debug("Strategy: explicit mode=%s", mode)
            return mode

        if task and task in TASK_STRATEGIES:
            decided = TASK_STRATEGIES[task]
            logger.debug("Strategy: task='%s' → mode='%s'", task, decided)
            return decided

        logger.debug("Strategy: fallback → mode='single'")
        return "single"