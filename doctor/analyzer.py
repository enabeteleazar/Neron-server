# app/analyzer.py
# Analyse statique avancée : filesystem + AST Python + détection d'anomalies

import ast
import os
import importlib.util
from typing import Any
from doctor.config import cfg
from doctor.logger import get_logger

log = get_logger("doctor.analyzer")

# Patterns de fichiers ignorés
IGNORE_DIRS  = {"__pycache__", ".git", ".venv", "node_modules", ".mypy_cache"}
IGNORE_EXTS  = {".pyc", ".pyo", ".log", ".DS_Store"}


# ─────────────────────────────────────────────
#  Analyse filesystem
# ─────────────────────────────────────────────

def analyze_project(path: str) -> dict[str, Any]:
    log.info(f"Analyzing project at: {path}")

    result: dict[str, Any] = {
        "path": path,
        "exists": os.path.exists(path),
        "files": [],
        "python_files": [],
        "entrypoints": [],
        "issues": [],
        "syntax_errors": [],
        "missing_imports": [],
        "stats": {
            "total_files": 0,
            "total_lines": 0,
            "python_files": 0,
        },
    }

    if not result["exists"]:
        result["issues"].append(f"Path does not exist: {path}")
        log.warning(f"Path not found: {path}")
        return result

    entrypoint_names = {"main.py", "doctor.py", "server.py", "__main__.py"}

    for root, dirs, files in os.walk(path):
        # Prune les dossiers ignorés in-place
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for fname in files:
            if any(fname.endswith(ext) for ext in IGNORE_EXTS):
                continue

            full_path = os.path.join(root, fname)
            rel_path  = os.path.relpath(full_path, path)
            result["files"].append(rel_path)
            result["stats"]["total_files"] += 1

            if fname in entrypoint_names:
                result["entrypoints"].append(rel_path)

            if fname.endswith(".py"):
                result["python_files"].append(rel_path)
                result["stats"]["python_files"] += 1
                _analyze_python_file(full_path, rel_path, result)

    if not result["entrypoints"]:
        result["issues"].append("No entrypoint detected (main.py / doctor.py / server.py)")

    log.info(
        f"Analysis done: {result['stats']['total_files']} files, "
        f"{result['stats']['python_files']} Python, "
        f"{len(result['issues'])} issues"
    )
    return result


# ─────────────────────────────────────────────
#  Analyse AST d'un fichier Python
# ─────────────────────────────────────────────

def _analyze_python_file(full_path: str, rel_path: str, result: dict) -> None:
    try:
        with open(full_path, encoding="utf-8", errors="replace") as f:
            source = f.read()
    except OSError as e:
        result["issues"].append(f"Cannot read {rel_path}: {e}")
        return

    # Comptage lignes
    lines = source.splitlines()
    result["stats"]["total_lines"] += len(lines)

    # Vérification syntaxe
    try:
        tree = ast.parse(source, filename=full_path)
    except SyntaxError as e:
        err = {
            "file": rel_path,
            "line": e.lineno,
            "msg": str(e.msg),
        }
        result["syntax_errors"].append(err)
        result["issues"].append(f"Syntax error in {rel_path}:{e.lineno} — {e.msg}")
        log.error(f"Syntax error: {rel_path}:{e.lineno} — {e.msg}")
        return

    # Analyse des imports
    _check_imports(tree, rel_path, result)

    # Détection de patterns problématiques
    _check_patterns(tree, rel_path, result)


def _check_imports(tree: ast.AST, rel_path: str, result: dict) -> None:
    """Vérifie que les modules importés sont disponibles dans l'env."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module_name = None

            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    _test_import(module_name, rel_path, result)

            elif isinstance(node, ast.ImportFrom) and node.module:
                # Ignore les imports relatifs
                if node.level == 0:
                    module_name = node.module.split(".")[0]
                    _test_import(module_name, rel_path, result)


_import_cache: dict[str, bool] = {}

def _test_import(module: str, rel_path: str, result: dict) -> None:
    # stdlib ou déjà testé → skip
    if module in _import_cache:
        if not _import_cache[module]:
            result["missing_imports"].append({"file": rel_path, "module": module})
        return

    try:
        spec = importlib.util.find_spec(module)
        _import_cache[module] = spec is not None
    except (ModuleNotFoundError, ValueError):
        _import_cache[module] = False

    if not _import_cache[module]:
        result["missing_imports"].append({"file": rel_path, "module": module})
        result["issues"].append(f"Missing import '{module}' in {rel_path}")
        log.warning(f"Missing import: {module} ({rel_path})")


def _check_patterns(tree: ast.AST, rel_path: str, result: dict) -> None:
    """Détection de patterns dangereux ou dépréciés."""
    for node in ast.walk(tree):
        # bare except
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            result["issues"].append(f"Bare 'except:' found in {rel_path}:{node.lineno}")

        # print() en production (heuristique)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "print":
                result["issues"].append(
                    f"print() call in {rel_path}:{node.lineno} (use logger instead)"
                )
