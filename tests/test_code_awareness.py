import pytest

from modules.code_awareness.analyzer import analyze_file
from modules.code_awareness.architecture_mapper import map_architecture
from modules.code_awareness.dependency_mapper import map_dependencies
from modules.code_awareness.reader import read_file
from modules.code_awareness.scanner import scan_project
from modules.code_awareness.searcher import search_code
from modules.code_awareness.security import CodeAwarenessSecurityError


def _flatten_tree(node):
    paths = [node.get("path")]
    for child in node.get("children", []):
        paths.extend(_flatten_tree(child))
    return paths


def test_scanner_ignores_denied_directories():
    scan = scan_project(max_depth=4)
    paths = _flatten_tree(scan["tree"])

    assert "node_modules" not in paths
    assert ".git" not in paths
    assert "data" not in paths
    assert scan["modules"] > 0


def test_reader_refuses_sensitive_and_traversal_paths():
    with pytest.raises(CodeAwarenessSecurityError):
        read_file(".env")

    with pytest.raises(CodeAwarenessSecurityError):
        read_file("../etc/passwd")


def test_searcher_finds_create_skeleton():
    result = search_code("create_skeleton", max_results=20)
    files = {item["file"] for item in result["results"]}

    assert "core/planning/planner.py" in files or "core/planning/executor.py" in files


def test_analyzer_detects_ast_structures():
    result = analyze_file("core/goals/goal_orchestrator.py")

    assert any(item["name"] == "GoalOrchestrator" for item in result["classes"])
    assert result["functions"] or result["classes"]
    assert "dependencies" in result


def test_dependency_mapper_returns_coherent_graph():
    result = map_dependencies(max_files=80)

    assert result["nodes"]
    assert "summary" in result
    assert result["summary"]["modules"] == len(result["nodes"])


def test_architecture_mapper_returns_global_view():
    result = map_architecture()

    assert result["name"] == "Neron"
    assert result["summary"]["architecture_known"] is True
    assert any(group["name"] == "Cognition" for group in result["groups"])
