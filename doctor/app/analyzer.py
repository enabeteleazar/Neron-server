# app/analyzer.py
# analyse structure + fichiers

import os


def analyze_project(path):
    result = {
        "path": path,
        "files": [],
        "entrypoints": [],
        "issues": []
    }

    for root, dirs, files in os.walk(path):
        for f in files:
            full = os.path.join(root, f)
            result["files"].append(full)

            # détection simple entrypoints
            if f in ["main.py", "app.py", "server.py"]:
                result["entrypoints"].append(full)

            # détection basique erreurs structurelles
            if f.endswith(".py") and "test" in f:
                result["issues"].append(f"Test file found: {f}")

    if not result["entrypoints"]:
        result["issues"].append("No entrypoint detected")

    return result
