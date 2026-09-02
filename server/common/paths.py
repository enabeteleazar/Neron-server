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


def _env_path(name: str) -> Path | None:
    """Resolve an environment variable to an absolute path when present."""
    value = os.getenv(name)
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else (Path.cwd() / path).resolve(strict=False)


def _iter_project_roots(start: Path | None = None) -> list[Path]:
    """Walk upward from the current file or working directory to find the NeronOS root."""
    seen: set[Path] = set()
    bases = [start] if start is not None else []
    bases.extend([Path(__file__).resolve(), Path.cwd()])

    roots: list[Path] = []
    for base in bases:
        current = base if base.is_dir() else base.parent
        while True:
            current = current.resolve(strict=False)
            if current not in seen:
                seen.add(current)
                roots.append(current)
            if current.parent == current:
                break
            current = current.parent

    return roots


def find_neron_home() -> Path:
    """Resolve the NeronOS root without relying on NERON_ROOT being set.

    Priority: (1) NERON_ROOT env var, (2) directory scan from this file / cwd
    up to a directory that looks like the project root, (3) NERON_ROOT default.
    Used where a component may run before the standard environment (normally
    set by systemd) is available — most callers should use NERON_ROOT instead.
    """
    env_root = _env_path("NERON_ROOT")
    if env_root is not None:
        return env_root.resolve(strict=False)

    for candidate in _iter_project_roots():
        if (candidate / "server" / "core").exists() and (
            (candidate / "neron.yaml").exists() or (candidate / "neron.server.yaml").exists()
        ):
            return candidate.resolve(strict=False)

    return NERON_ROOT.resolve(strict=False)
