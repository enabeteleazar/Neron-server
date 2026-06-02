from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


PROJECTS_PATH = Path("/etc/neron/data/projects.json")


def _now() -> float:
    return time.time()


class ProjectManager:
    def __init__(self, path: Path = PROJECTS_PATH) -> None:
        self.path = path

    def create_project(
        self,
        *,
        title: str,
        project_type: str,
        requested_by: str = "user",
        source_channel: str = "api",
        query: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        projects = self._load()
        project_id = self._make_project_id(title, project_type)
        created_at = _now()
        project = {
            "project_id": project_id,
            "title": title,
            "type": project_type,
            "status": "pending",
            "current_step": "created",
            "progress": 0,
            "requested_by": requested_by,
            "source_channel": source_channel,
            "query": query,
            "created_at": created_at,
            "updated_at": created_at,
            "steps": [],
            "created_files": [],
            "test_results": [],
            "registry_status": "not_registered",
            "result": None,
            "error": None,
            "metadata": metadata or {},
        }
        projects.append(project)
        self._save(projects)
        return project

    def update_project(
        self,
        project_id: str,
        updates: dict[str, Any] | None = None,
        *,
        step: str | None = None,
        step_status: str | None = None,
        progress: int | None = None,
        error: str | None = None,
    ) -> dict[str, Any] | None:
        projects = self._load()
        for project in projects:
            if project.get("project_id") != project_id:
                continue

            if step:
                project["current_step"] = step
                project.setdefault("steps", []).append(
                    {
                        "name": step,
                        "status": step_status or "done",
                        "at": _now(),
                        "error": error,
                    }
                )
            if updates:
                project.update(updates)
            if progress is not None:
                project["progress"] = max(0, min(100, int(progress)))
            if error:
                project["error"] = error
            project["updated_at"] = _now()
            self._save(projects)
            return project
        return None

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        for project in self._load():
            if project.get("project_id") == project_id:
                return project
        return None

    def list_projects(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        projects = self._load()
        if status:
            projects = [project for project in projects if project.get("status") == status]
        return list(reversed(projects[-max(1, min(limit, 500)):]))

    def find_project_by_query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        normalized = self._normalize(query)
        keywords = [word for word in normalized.split() if len(word) >= 3]
        if not keywords:
            return []

        matches = []
        for project in reversed(self._load()):
            haystack = self._normalize(
                " ".join(
                    str(project.get(field) or "")
                    for field in ("project_id", "title", "type", "query")
                )
            )
            metadata = project.get("metadata") or {}
            haystack += " " + self._normalize(json.dumps(metadata, ensure_ascii=False))
            if all(keyword in haystack for keyword in keywords[:3]) or any(
                keyword in haystack for keyword in keywords
            ):
                matches.append(project)
            if len(matches) >= limit:
                break
        return matches

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []
        projects = data.get("projects", []) if isinstance(data, dict) else []
        return projects if isinstance(projects, list) else []

    def _save(self, projects: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"projects": projects[-500:]}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _make_project_id(self, title: str, project_type: str) -> str:
        words = [
            word
            for word in self._normalize(title).split()
            if word not in {"creer", "agent", "tool", "outil", "pour", "avec", "qui", "me", "donne"}
        ]
        base = "_".join(words[:4]) or project_type
        return f"{project_type}_{base}_{uuid.uuid4().hex[:8]}"

    def _normalize(self, value: str) -> str:
        import unicodedata

        text = unicodedata.normalize("NFD", value.lower())
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        cleaned = []
        for char in text:
            cleaned.append(char if char.isalnum() else " ")
        return " ".join("".join(cleaned).split())


_project_manager: ProjectManager | None = None


def get_project_manager() -> ProjectManager:
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager()
    return _project_manager
