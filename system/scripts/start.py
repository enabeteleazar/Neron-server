#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/etc/neron")
VENV = ROOT / "venv"
PYTHON = VENV / "bin" / "python"
PIP = VENV / "bin" / "pip"

SECRETS_ENV = ROOT / "secrets.env"
NETWORK_ENV = ROOT / "system" / "config" / "network.env"
REQUIREMENTS = ROOT / "system" / "requirements" / "requirements.txt"


ROLES = {
    "core": {
        "module": "core.app:app",
        "host_env": "NERON_CORE_HOST",
        "port_env": "NERON_CORE_PORT",
        "default_host": "0.0.0.0",
        "default_port": "8010",
        "pythonpath": "/etc/neron/server:/etc/neron/server/llm",
    },
    "llm": {
        "module": "llm.app:app",
        "host_env": "NERON_LLM_HOST",
        "port_env": "NERON_LLM_PORT",
        "default_host": "0.0.0.0",
        "default_port": "8765",
        "pythonpath": "/etc/neron/server:/etc/neron/server/llm",
    },
    "memory": {
        "module": "memory.app:app",
        "host_env": "NERON_MEMORY_HOST",
        "port_env": "NERON_MEMORY_PORT",
        "default_host": "0.0.0.0",
        "default_port": "8040",
        "pythonpath": "/etc/neron/server",
        "extra_env": {
            "NERON_SERVICE_HOST": "u4-neron-memory",
            "NERON_SERVICE_PORT": "8040",
        },
    },
    "goal": {
        "module": "goal.app:app",
        "host_env": "NERON_GOAL_HOST",
        "port_env": "NERON_GOAL_PORT",
        "default_host": "0.0.0.0",
        "default_port": "8030",
        "pythonpath": "/etc/neron/server",
        "extra_env": {
            "NERON_SERVICE_HOST": "u6-neron-goal",
            "NERON_SERVICE_PORT": "8030",
        },
    },
}


def run(cmd: list[str], env: dict[str, str] | None = None) -> None:
    print(f"[start.py] $ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, env=env)


def load_env_file(path: Path) -> dict[str, str]:
    env = {}

    if not path.exists():
        return env

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key:
            env[key] = value

    return env


def ensure_venv() -> None:
    if PYTHON.exists() and PIP.exists():
        print("[start.py] venv OK")
        return

    print("[start.py] venv absent ou incomplet, recréation...")

    run(["python3", "-m", "venv", str(VENV)])

    if not PYTHON.exists():
        raise RuntimeError("Impossible de créer le venv Python.")


def install_requirements() -> None:
    if not REQUIREMENTS.exists():
        print(f"[start.py] Aucun requirements trouvé : {REQUIREMENTS}")
        return

    marker = VENV / ".requirements-installed"

    req_mtime = REQUIREMENTS.stat().st_mtime
    marker_mtime = marker.stat().st_mtime if marker.exists() else 0

    if marker.exists() and marker_mtime >= req_mtime:
        print("[start.py] requirements déjà installés")
        return

    print("[start.py] installation des requirements...")

    run([str(PYTHON), "-m", "pip", "install", "-U", "pip"])
    run([str(PIP), "install", "-r", str(REQUIREMENTS)])

    marker.write_text("ok\n")


def build_env(role: str) -> dict[str, str]:
    cfg = ROLES[role]

    env = os.environ.copy()
    env.update(load_env_file(SECRETS_ENV))
    env.update(load_env_file(NETWORK_ENV))

    env["PYTHONPATH"] = cfg["pythonpath"]

    for key, value in cfg.get("extra_env", {}).items():
        env.setdefault(key, value)

    return env


def start_role(role: str) -> None:
    cfg = ROLES[role]
    env = build_env(role)

    host = env.get(cfg["host_env"], cfg["default_host"])
    port = env.get(cfg["port_env"], cfg["default_port"])

    print(f"[start.py] rôle      : {role}")
    print(f"[start.py] module    : {cfg['module']}")
    print(f"[start.py] host      : {host}")
    print(f"[start.py] port      : {port}")
    print(f"[start.py] PYTHONPATH: {env['PYTHONPATH']}")

    cmd = [
        str(PYTHON),
        "-m",
        "uvicorn",
        cfg["module"],
        "--host",
        host,
        "--port",
        str(port),
    ]

    os.execve(str(PYTHON), cmd, env)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ROLES:
        print("Usage: start.py {core|llm|memory|goal}")
        sys.exit(1)

    role = sys.argv[1]

    os.chdir(ROOT)

    ensure_venv()
    install_requirements()
    start_role(role)


if __name__ == "__main__":
    main()
