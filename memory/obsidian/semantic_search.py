from memory.obsidian.vector_index import ObsidianVectorIndex


class ObsidianSemanticSearch:
    def __init__(self, vault_path: str):
        self.index = ObsidianVectorIndex(vault_path)

    def rebuild(self) -> dict:
        return self.index.build()

    def search(self, query: str, limit: int = 5, min_score: float = 0.15) -> list[dict]:
        results = self.index.search(query, limit=limit)

        return [
            result for result in results
            if result.get("score", 0) >= min_score
        ]
