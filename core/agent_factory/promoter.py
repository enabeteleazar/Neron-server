from __future__ import annotations

import shutil
from pathlib import Path


GENERATED_DIR = Path("/etc/neron/core/agents/generated")


def promote_agent(path: str, generated_dir: str | Path | None = None) -> dict:
    src = Path(path)

    if not src.exists():
        return {
            "ok": False,
            "error": "agent introuvable",
        }

    target_dir = Path(generated_dir) if generated_dir is not None else GENERATED_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    dst = target_dir / src.name

    shutil.copy2(src, dst)

    return {
        "ok": True,
        "source": str(src),
        "destination": str(dst),
    }
