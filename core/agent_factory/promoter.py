from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


GENERATED_DIR = Path("/etc/neron/core/agents/generated")


def promote_agent(
    path: str,
    generated_dir: str | Path | None = None,
    *,
    runtime_governor: Any | None = None,
    requested_by: str = "legacy_promoter",
) -> dict:
    src = Path(path)

    if not src.exists():
        return {
            "ok": False,
            "error": "agent introuvable",
        }

    if runtime_governor is None:
        from core.runtime.governor import get_runtime_governor

        runtime_governor = get_runtime_governor()
    agent_name = src.stem
    if not runtime_governor.authorize_agent_promotion(
        agent_name=agent_name,
        requested_by=requested_by,
    ):
        return {
            "ok": False,
            "error": "runtime_governor_refused",
            "governor_status": "refused",
            "governor_policy": runtime_governor.to_dict(),
        }

    target_dir = Path(generated_dir) if generated_dir is not None else GENERATED_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    dst = target_dir / src.name

    shutil.copy2(src, dst)

    return {
        "ok": True,
        "source": str(src),
        "destination": str(dst),
        "governor_status": "allowed",
    }
