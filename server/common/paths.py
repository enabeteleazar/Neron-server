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
