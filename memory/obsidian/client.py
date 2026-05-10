from pathlib import Path
from datetime import datetime
import re


class ObsidianMemory:
    def __init__(self, vault_path: str):
        self.vault = Path(vault_path)
        self.vault.mkdir(parents=True, exist_ok=True)

    def _safe_filename(self, title: str) -> str:
        title = title.strip().lower()
        title = re.sub(r"[^a-zA-Z0-9À-ÿ\-_\s]", "", title)
        title = re.sub(r"\s+", "-", title)
        return title[:80] or "note"

    def write_note(self, folder: str, title: str, content: str, tags=None) -> str:
        tags = tags or []
        target_dir = self.vault / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = self._safe_filename(title)
        path = target_dir / f"{filename}.md"

        now = datetime.now().isoformat(timespec="seconds")

        markdown = f"""# {title}

Date: {now}
Tags: {" ".join("#" + tag for tag in tags)}

---

{content}
"""

        path.write_text(markdown, encoding="utf-8")
        return str(path)

    def append_note(self, folder: str, title: str, content: str) -> str:
        target_dir = self.vault / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = self._safe_filename(title)
        path = target_dir / f"{filename}.md"

        now = datetime.now().isoformat(timespec="seconds")

        with path.open("a", encoding="utf-8") as f:
            f.write(f"\n\n## Ajout du {now}\n\n{content}\n")

        return str(path)

    def search(self, query: str, limit: int = 10):
        results = []
        query_lower = query.lower()

        for file in self.vault.rglob("*.md"):
            try:
                text = file.read_text(encoding="utf-8")
            except Exception:
                continue

            if query_lower in text.lower() or query_lower in file.name.lower():
                results.append({
                    "file": str(file),
                    "title": file.stem,
                    "preview": text[:500]
                })

            if len(results) >= limit:
                break

        return results

    def read_note(self, relative_path: str) -> str:
        path = self.vault / relative_path
        if not path.exists():
            raise FileNotFoundError(f"Note introuvable : {relative_path}")
        return path.read_text(encoding="utf-8")
