"""Canonical runtime paths for NeronOS.

Every path can be overridden for development or alternate deployments while
keeping /etc/neronOS as the production default.
"""

from __future__ import annotations

import os
from pathlib import Path


NERON_ROOT = Path(os.getenv("NERON_ROOT", "/etc/neronOS")).expanduser()
NERON_CONFIG = Path(
    os.getenv("NERON_CONFIG", str(NERON_ROOT / "neron.yaml"))
).expanduser()
NERON_DATA_DIR = Path(
    os.getenv("NERON_DATA_DIR", str(NERON_ROOT / "data"))
).expanduser()
NERON_SERVER_DIR = Path(
    os.getenv("NERON_SERVER_DIR", str(NERON_ROOT / "server"))
).expanduser()
NERON_WORKSPACE_DIR = Path(
    os.getenv("NERON_WORKSPACE_DIR", str(NERON_ROOT / "workspace"))
).expanduser()


def service_version(start: str, default: str = "0.0.0") -> str:
    """Version du service, lue depuis le premier fichier VERSION trouve.

    `start` est le chemin du module appelant, typiquement `__file__`.
    Le prefixe v/V eventuel est retire.
    """

    for parent in Path(start).resolve().parents:

        candidate = parent / "VERSION"

        if candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8").strip()
            except OSError:
                break

            if text:
                return text.lstrip("vV")

    return default
NERON_SECRETS_FILE = Path(
    os.getenv("NERON_SECRETS_FILE", str(NERON_ROOT / "secrets.env"))
).expanduser()
NERON_IDENTITY_PATH = Path(
    os.getenv(
        "NERON_IDENTITY_PATH",
        str(NERON_SERVER_DIR / "memory" / "obsidian" / "identity" / "NERON.md"),
    )
).expanduser()
