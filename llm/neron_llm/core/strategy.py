# neron_llm/core/strategy.py
#Strategy layer — decides execution mode automatically based on task type.

from __future__ import annotations
import logging

logger = logging.getLogger("neron_llm.strategy")

# ── Built-in task → mode defaults ─────────────────────────────────────────────

_DEFAULT_TASK_STRATEGIES: dict[str, str] = {
    # public bus task_types
    "code":      "parallel",   # run on all providers, pick best
    "reasoning": "single",     # depth over breadth
    "chat":      "race",       # first answer wins — low latency
    "agent":     "single",     # controlled, memory-augmented future
    # internal
    "fast":      "single",
    "summary":   "single",
    "default":   "single",
}


class StrategyEngine:

    def __init__(self) -> None:
        # Load yaml overrides at construction — config is cached by lru_cache
        self._strategies = dict(_DEFAULT_TASK_STRATEGIES)
        try:
            from neron_llm.config import load_config
            cfg_strategies: dict = load_config().get("strategy", {})
            valid_modes = {"single", "parallel", "race"}
            for task, mode in cfg_strategies.items():
                if mode in valid_modes:
                    self._strategies[task] = mode
                    logger.debug("Strategy override: task='%s' → mode='%s'", task, mode)
                else:
                    logger.warning(
                        "Strategy: invalid mode '%s' for task '%s' in config — ignored",
                        mode, task,
                    )
        except Exception as exc:
            logger.warning("Strategy: could not load yaml overrides: %s", exc)

        logger.debug("StrategyEngine initialized — table: %s", self._strategies)

    def decide(self, task: str | None = None, mode: str | None = None) -> str:
        """Return the execution mode.

        Priority: explicit mode override > task-based strategy > 'single'.
        """
        if mode:
            logger.debug("Strategy: explicit mode='%s'", mode)
            return mode

        if task and task in self._strategies:
            decided = self._strategies[task]
            logger.debug("Strategy: task='%s' → mode='%s'", task, decided)
            return decided

        logger.debug("Strategy: unknown task='%s' → fallback mode='single'", task)
        return "single"
