# app/fixer.py
# autocorrection simple

import subprocess


def apply_fixes(report):
    fixes = []

    tests = report.get("tests", {})

    # Exemple: redémarrage server si down
    if isinstance(tests.get("server_health"), str):
        subprocess.run(["systemctl", "restart", "neron-server"])
        fixes.append("Restarted neron-server")

    if isinstance(tests.get("llm_health"), str):
        subprocess.run(["systemctl", "restart", "neron-llm"])
        fixes.append("Restarted neron-llm")

    return fixes
