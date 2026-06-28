"""agents/internal/code_tools.py
Utilities for code agent: path safety, backups, sandbox, syntax checks, file listing.
"""
from __future__ import annotations

import shutil
import tempfile
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List


# Determine repo root (/etc/neron)
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = REPO_ROOT / "server" / "data" / "code_backups"
EXCLUDE_DIRS = {"__pycache__", "venv", ".git", "data", "docs", "scripts"}
PY_EXT = {".py"}
SANDBOX_TIMEOUT = 10


def safe_path(raw: str, generated: bool = False) -> Path:
    if generated:
        workspace = Path("/mnt/usb-storage/neron/workspace")
        target = (workspace / Path(raw).name).resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        return target
    target = (REPO_ROOT / raw).resolve()
    if not str(target).startswith(str(REPO_ROOT)):
        raise ValueError(f"Chemin non autorisé (hors workspace) : {raw!r}")
    return target


def backup(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        rel = path.relative_to(REPO_ROOT)
    except Exception:
        rel = path
    safe_name = str(rel).replace("/", "_").replace("\\", "_")
    dest = BACKUP_DIR / f"{safe_name}.{ts}.bak"
    shutil.copy2(path, dest)
    existing = sorted(BACKUP_DIR.glob(f"{safe_name}.*.bak"))
    for old in existing[:-10]:
        old.unlink(missing_ok=True)
    return dest


def rollback(path: Path) -> bool:
    try:
        rel = path.relative_to(REPO_ROOT)
    except Exception:
        rel = path
    safe_name = str(rel).replace("/", "_").replace("\\", "_")
    backups = sorted(BACKUP_DIR.glob(f"{safe_name}.*.bak"))
    if not backups:
        return False
    shutil.copy2(backups[-1], path)
    return True


def strip_markdown_fences(code: str) -> str:
    code = re.sub(r"^```python\s*\n?", "", code.strip())
    code = re.sub(r"^```\s*\n?",       "", code.strip())
    code = re.sub(r"\n?```$",          "", code.strip())
    return code.strip()


async def sandbox_test(code: str) -> dict:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = Path(f.name)
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", str(tmp),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=SANDBOX_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {"ok": False, "stdout": "", "stderr": f"Timeout ({SANDBOX_TIMEOUT}s)"}
        return {"ok": proc.returncode == 0, "stdout": stdout.decode(), "stderr": stderr.decode()}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}
    finally:
        tmp.unlink(missing_ok=True)


async def check_syntax(code: str) -> dict:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = Path(f.name)
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-m", "py_compile", str(tmp),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        return {"ok": proc.returncode == 0, "stderr": stderr.decode()}
    finally:
        tmp.unlink(missing_ok=True)


def list_source_files() -> List[Path]:
    files = []
    for p in REPO_ROOT.rglob("*.py"):
        if p.name == "__init__.py":
            continue
        if not any(excl in p.parts for excl in EXCLUDE_DIRS):
            files.append(p)
    return sorted(files)


def collect_py_files(root: Path) -> List[Path]:
    files = []
    for p in root.rglob("*.py"):
        if not any(excl in p.parts for excl in EXCLUDE_DIRS):
            files.append(p)
    return sorted(files)
