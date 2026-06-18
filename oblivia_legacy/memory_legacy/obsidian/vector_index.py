from pathlib import Path
from datetime import datetime
import json
import numpy as np

from oblivia.memory_legacy.obsidian.embedder import LocalEmbedder


class ObsidianVectorIndex:
    def __init__(self, vault_path: str):
        self.vault = Path(vault_path)
        self.index_path = self.vault / "vector_index.json"
        self.embedder = LocalEmbedder()

    def build(self) -> dict:
        notes = []

        for file in self.vault.rglob("*.md"):
            if file.name in {"index.json", "vector_index.json"}:
                continue

            try:
                text = file.read_text(encoding="utf-8")
            except Exception:
                continue

            if not text.strip():
                continue

            relative = str(file.relative_to(self.vault))
            embedding = self.embedder.embed(text[:3000])

            notes.append({
                "path": relative,
                "title": file.stem,
                "folder": file.parent.name,
                "updated_at": datetime.fromtimestamp(file.stat().st_mtime).isoformat(timespec="seconds"),
                "preview": text[:500],
                "embedding": embedding,
            })

        data = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "model": self.embedder.model_name if self.embedder.model else "fallback-hash-embedding",
            "count": len(notes),
            "notes": notes,
        }

        self.index_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return data

    def load(self) -> dict:
        if not self.index_path.exists():
            return self.build()

        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def search(self, query: str, limit: int = 5) -> list[dict]:
        data = self.load()
        notes = data.get("notes", [])

        if not notes:
            return []

        query_vector = np.array(self.embedder.embed(query), dtype=float)

        results = []

        for note in notes:
            embedding = np.array(note.get("embedding", []), dtype=float)

            if embedding.size == 0:
                continue

            score = float(np.dot(query_vector, embedding))

            results.append({
                "score": round(score, 4),
                "path": note["path"],
                "title": note["title"],
                "folder": note["folder"],
                "preview": note["preview"],
                "updated_at": note["updated_at"],
            })

        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:limit]
