from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from memory.semantic.chunker import SemanticChunker


class ObsidianSemanticSearch:
    def __init__(
        self,
        vault_path: str,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ):
        self.vault_path = Path(vault_path)
        self.model_name = model_name

        self.model = SentenceTransformer(model_name)

        self.chunker = SemanticChunker()

        self.index_path = (
            self.vault_path / ".semantic_index.json"
        )

        self.index = []

    def build_index(self) -> dict:
        self.index = []

        markdown_files = list(
            self.vault_path.rglob("*.md")
        )

        total_chunks = 0

        for md_file in markdown_files:
            try:
                content = md_file.read_text(
                    encoding="utf-8"
                )

                relative_path = str(
                    md_file.relative_to(self.vault_path)
                )

                chunks = self.chunker.chunk_markdown(
                    content,
                    source=relative_path,
                )

                for chunk in chunks:
                    embedding = self.model.encode(
                        chunk["content"]
                    ).tolist()

                    entry = {
                        "id": chunk["id"],
                        "path": relative_path,
                        "content": chunk["content"],
                        "hash": chunk["hash"],
                        "size": chunk["size"],
                        "embedding": embedding,
                    }

                    self.index.append(entry)

                    total_chunks += 1

            except Exception as exc:
                print(
                    f"[semantic] erreur indexation {md_file}: {exc}"
                )

        self.index_path.write_text(
            json.dumps(
                self.index,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return {
            "success": True,
            "indexed_notes": len(markdown_files),
            "indexed_chunks": total_chunks,
            "index_path": str(self.index_path),
            "model": self.model_name,
        }

    def load_index(self) -> None:
        if not self.index_path.exists():
            return

        self.index = json.loads(
            self.index_path.read_text(
                encoding="utf-8"
            )
        )

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> List[dict]:

        if not self.index:
            self.load_index()

        if not self.index:
            return []

        query_embedding = self.model.encode(query)

        results = []

        for entry in self.index:
            score = self._cosine_similarity(
                query_embedding,
                np.array(entry["embedding"]),
            )

            results.append(
                {
                    "score": round(float(score), 4),
                    "path": entry["path"],
                    "content": entry["content"][:500],
                    "id": entry["id"],
                }
            )

        results.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        return results[:limit]

    def _cosine_similarity(
        self,
        a,
        b,
    ) -> float:
        return np.dot(a, b) / (
            np.linalg.norm(a)
            * np.linalg.norm(b)
        )
