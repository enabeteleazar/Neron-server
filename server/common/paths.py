"""Canonical runtime paths for NeronOS.

Every path can be overridden for development or alternate deployments while
keeping /srv/homelab/server-1/neronOS as the production default.
"""

from __future__ import annotations

import os
from pathlib import Path


NERON_ROOT = Path(os.getenv("NERON_ROOT", "/srv/homelab/server-1/neronOS")).expanduser()
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
NERON_SECRETS_FILE = Path(
    os.getenv("NERON_SECRETS_FILE", str(NERON_ROOT / "secrets.env"))
).expanduser()
NERON_IDENTITY_PATH = Path(
    os.getenv(
        "NERON_IDENTITY_PATH",
        str(NERON_SERVER_DIR / "memory" / "obsidian" / "identity" / "NERON.md"),
    )
).expanduser()
