from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from core.code_awareness.analyzer import analyze_file
from core.code_awareness.architecture_mapper import map_architecture
from core.code_awareness.dependency_mapper import map_dependencies
from core.code_awareness.reader import read_file
from core.code_awareness.scanner import scan_project
from core.code_awareness.searcher import search_code
from core.code_awareness.security import CodeAwarenessSecurityError


router = APIRouter(prefix="/code-awareness", tags=["code-awareness"])


@router.get("/map")
async def code_awareness_map() -> dict:
    scan = scan_project(max_depth=2)
    architecture = map_architecture()
    return {
        "scan": {
            "files": scan["files"],
            "modules": scan["modules"],
            "packages": scan["packages"][:30],
        },
        "architecture": architecture,
    }


@router.get("/tree")
async def code_awareness_tree(max_depth: Annotated[int, Query(ge=1, le=6)] = 3) -> dict:
    return scan_project(max_depth=max_depth)


@router.get("/read")
async def code_awareness_read(
    path: str,
    start_line: Annotated[int, Query(ge=1)] = 1,
    max_lines: Annotated[int, Query(ge=1, le=400)] = 120,
) -> dict:
    try:
        return read_file(path, start_line=start_line, max_lines=max_lines)
    except (CodeAwarenessSecurityError, FileNotFoundError, IsADirectoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/search")
async def code_awareness_search(
    query: str,
    max_results: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    return search_code(query, max_results=max_results)


@router.get("/analyze")
async def code_awareness_analyze(path: str) -> dict:
    try:
        return analyze_file(path)
    except (CodeAwarenessSecurityError, FileNotFoundError, IsADirectoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dependencies")
async def code_awareness_dependencies(
    max_files: Annotated[int, Query(ge=1, le=1000)] = 250,
) -> dict:
    return map_dependencies(max_files=max_files)


@router.get("/architecture")
async def code_awareness_architecture() -> dict:
    return map_architecture()
