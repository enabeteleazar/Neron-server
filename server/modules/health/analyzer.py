# doctor/analyzer.py
# Analyse statique d'un projet Python : structure, entrypoints, syntax errors

import os
import py_compile

# Dossiers à ignorer complètement
EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "venv", ".venv", "node_modules"}

# Fichiers considérés comme entrypoints
ENTRYPOINT_NAMES = {"main.py", "app.py", "server.py"}


def check_syntax(filepath: str) -> str | None:
    """Retourne le message d'erreur si syntax error, None si OK."""
    try:
        py_compile.compile(filepath, doraise=True)
        return None
    except py_compile.PyCompileError as e:
        return str(e)


def analyze_project(path: str) -> dict:
    result = {
        "path": path,
        "exists": False,
        "files": [],
        "entrypoints": [],
        "issues": [],
        "syntax_errors": [],
    }

    if not os.path.exists(path):
        result["issues"].append(f"Path does not exist: {path}")
        return result

    result["exists"] = True

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for f in files:
            full = os.path.join(root, f)
            result["files"].append(full)

            # Détection entrypoints
            if f in ENTRYPOINT_NAMES:
                result["entrypoints"].append(full)

            # Détection fichiers de test
            if f.endswith(".py") and "test" in f.lower():
                result["issues"].append(f"Test file found: {f}")

            # Vérification syntaxe
            if f.endswith(".py"):
                error = check_syntax(full)
                if error:
                    result["syntax_errors"].append({
                        "file": full,
                        "error": error,
                    })

    if result["exists"] and not result["entrypoints"]:
        result["issues"].append("No entrypoint detected")

    return result
