#!/usr/bin/env python3

import os
import signal
import subprocess
import sys

SERVICES = {
    "core": "core.app",
    "llm": "llm.app",
    "memory": "memory.app",
    "goal": "goal.app",
}


def stop(service: str):
    pattern = f"uvicorn {SERVICES[service]}"

    result = subprocess.run(
        ["pgrep", "-f", pattern],
        capture_output=True,
        text=True,
    )

    pids = [pid for pid in result.stdout.split() if pid.strip()]

    if not pids:
        print(f"[stop.py] {service} déjà arrêté.")
        return

    for pid in pids:
        print(f"[stop.py] arrêt de {service} (PID {pid})")
        os.kill(int(pid), signal.SIGTERM)

    print(f"[stop.py] {service} arrêté.")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in SERVICES:
        print("Usage: stop.py {core|llm|memory|goal}")
        sys.exit(1)

    stop(sys.argv[1])


if __name__ == "__main__":
    main()
