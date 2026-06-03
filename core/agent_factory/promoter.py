from __future__ import annotations

import shutil
from pathlib import Path


GENERATED_DIR = Path("/etc/neron/core/agents/generated")


def promote_agent(path: str) -> dict:
    src = Path(path)

    if not src.exists():
        return {
            "ok": False,
            "error": "agent introuvable",
        }

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    dst = GENERATED_DIR / src.name

    shutil.copy2(src, dst)

    return {
        "ok": True,
        "source": str(src),
        "destination": str(dst),
    }
