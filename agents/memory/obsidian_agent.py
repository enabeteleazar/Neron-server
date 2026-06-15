from oblivia.memory_legacy.obsidian.client import ObsidianMemory
from oblivia.memory_legacy.obsidian.tagger import extract_tags, classify_folder
from oblivia.memory_legacy.obsidian.indexer import ObsidianIndexer
from oblivia.memory_legacy.obsidian.context_builder import ObsidianContextBuilder
from oblivia.memory_legacy.obsidian.semantic_search import ObsidianSemanticSearch


class ObsidianAgent:
    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.memory = ObsidianMemory(vault_path)
        self.indexer = ObsidianIndexer(vault_path)
        self.context_builder = ObsidianContextBuilder(vault_path)
        self.semantic = ObsidianSemanticSearch(vault_path)

    def handle(self, text: str) -> dict:
        lowered = text.lower().strip()

        if self._is_write_intent(lowered):
            return self._handle_write(text)

        if self._is_search_intent(lowered):
            return self._handle_search(text)

        if self._is_index_intent(lowered):
            return self._handle_index()

        if self._is_vector_index_intent(lowered):
            return self._handle_vector_index()

        if self._is_semantic_search_intent(lowered):
            return self._handle_semantic_search(text)

        return {
            "response": "Je n’ai pas compris l’action mémoire demandée.",
            "intent": "memory_unknown",
            "agent": "obsidian_agent",
            "error": "unknown_memory_action",
        }

    def build_context(self, query: str, limit: int = 3) -> str:
        return self.context_builder.build_context(query, limit=limit)

    def _handle_write(self, text: str) -> dict:
        content = self._clean_write_text(text)

        if not content:
            return {
                "response": "Je n’ai pas de contenu à enregistrer.",
                "intent": "memory_write",
                "agent": "obsidian_agent",
                "error": "empty_content",
            }

        folder = classify_folder(content)
        tags = extract_tags(content)

        if "neron" not in tags:
            tags.append("neron")

        path = self.memory.write_note(
            folder=folder,
            title=content[:60],
            content=content,
            tags=tags,
        )

        self.indexer.build_index()

        try:
            self.semantic.rebuild()
        except Exception:
            pass

        return {
            "response": f"Note enregistrée dans Obsidian : {path}",
            "intent": "memory_write",
            "agent": "obsidian_agent",
            "error": None,
            "metadata": {
                "folder": folder,
                "tags": tags,
                "path": path,
            },
        }

    def _handle_search(self, text: str) -> dict:
        query = self._clean_search_text(text)

        if not query:
            return {
                "response": "Quelle information dois-je chercher dans Obsidian ?",
                "intent": "memory_search",
                "agent": "obsidian_agent",
                "error": "empty_query",
            }

        results = self.memory.search(query)

        if not results:
            return {
                "response": "Je n’ai rien trouvé dans la mémoire Obsidian.",
                "intent": "memory_search",
                "agent": "obsidian_agent",
                "error": None,
            }

        formatted = "\n".join(
            f"- {result['title']} : {result['file']}"
            for result in results
        )

        return {
            "response": f"Résultats trouvés dans Obsidian :\n{formatted}",
            "intent": "memory_search",
            "agent": "obsidian_agent",
            "error": None,
            "metadata": {
                "query": query,
                "count": len(results),
                "results": results,
            },
        }

    def _handle_index(self) -> dict:
        index = self.indexer.build_index()

        return {
            "response": f"Index Obsidian reconstruit : {index['count']} notes indexées.",
            "intent": "memory_index",
            "agent": "obsidian_agent",
            "error": None,
            "metadata": index,
        }

    def _handle_vector_index(self) -> dict:
        index = self.semantic.rebuild()

        return {
            "response": (
                f"Index vectoriel Obsidian reconstruit : "
                f"{index['count']} notes indexées avec {index['model']}."
            ),
            "intent": "memory_vector_index",
            "agent": "obsidian_agent",
            "error": None,
            "metadata": index,
        }

    def _handle_semantic_search(self, text: str) -> dict:
        query = self._clean_semantic_search_text(text)

        if not query:
            return {
                "response": "Quelle information dois-je chercher sémantiquement dans Obsidian ?",
                "intent": "memory_semantic_search",
                "agent": "obsidian_agent",
                "error": "empty_query",
            }

        results = self.semantic.search(query, limit=5)

        if not results:
            return {
                "response": "Je n’ai rien trouvé avec la recherche sémantique Obsidian.",
                "intent": "memory_semantic_search",
                "agent": "obsidian_agent",
                "error": None,
            }

        formatted = "\n".join(
            f"- {result['title']} [{result['score']}] : {result['path']}"
            for result in results
        )

        return {
            "response": f"Résultats sémantiques Obsidian :\n{formatted}",
            "intent": "memory_semantic_search",
            "agent": "obsidian_agent",
            "error": None,
            "metadata": {
                "query": query,
                "count": len(results),
                "results": results,
            },
        }

    def _is_write_intent(self, text: str) -> bool:
        keywords = [
            "idée",
            "idee",
            "ajoute une idée",
            "ajoute une idee",
            "note ceci",
            "mémorise",
            "memorise",
            "sauvegarde ceci",
            "retient ceci",
            "enregistre ceci",
        ]
        return any(keyword in text for keyword in keywords)

    def _is_search_intent(self, text: str) -> bool:
        keywords = [
            "cherche dans obsidian",
            "recherche mémoire",
            "recherche memoire",
            "cherche dans la mémoire",
            "cherche dans la memoire",
            "retrouve mes notes",
            "recherche dans obsidian",
            "mémoire obsidian",
            "memoire obsidian",
        ]
        return any(keyword in text for keyword in keywords)

    def _is_index_intent(self, text: str) -> bool:
        keywords = [
            "reconstruis index obsidian",
            "reconstruire index obsidian",
            "index obsidian",
            "réindexe obsidian",
            "reindexe obsidian",
        ]
        return any(keyword in text for keyword in keywords)

    def _is_vector_index_intent(self, text: str) -> bool:
        keywords = [
            "index vectoriel obsidian",
            "reconstruis index vectoriel",
            "reconstruire index vectoriel",
            "réindexe vectoriel",
            "reindexe vectoriel",
        ]
        return any(keyword in text for keyword in keywords)

    def _is_semantic_search_intent(self, text: str) -> bool:
        keywords = [
            "cherche sémantiquement",
            "cherche semantiquement",
            "recherche sémantique",
            "recherche semantique",
            "semantic search",
        ]
        return any(keyword in text for keyword in keywords)

    def _clean_write_text(self, text: str) -> str:
        cleaned = text.strip()

        replacements = [
            "ajoute une idée",
            "ajoute une idee",
            "idée",
            "idee",
            "note ceci",
            "mémorise",
            "memorise",
            "sauvegarde ceci",
            "retient ceci",
            "enregistre ceci",
        ]

        for item in replacements:
            cleaned = cleaned.replace(item, "", 1)
            cleaned = cleaned.replace(item.capitalize(), "", 1)

        return cleaned.strip(" :,-")

    def _clean_search_text(self, text: str) -> str:
        cleaned = text.lower().strip()

        prefixes = [
            "cherche dans obsidian",
            "recherche mémoire",
            "recherche memoire",
            "cherche dans la mémoire",
            "cherche dans la memoire",
            "retrouve mes notes",
            "recherche dans obsidian",
            "mémoire obsidian",
            "memoire obsidian",
        ]

        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break

        return cleaned.strip(" :,-")

    def _clean_semantic_search_text(self, text: str) -> str:
        cleaned = text.lower().strip()

        prefixes = [
            "cherche sémantiquement dans obsidian",
            "cherche semantiquement dans obsidian",
            "recherche sémantique obsidian",
            "recherche semantique obsidian",
            "cherche sémantiquement",
            "cherche semantiquement",
            "recherche sémantique",
            "recherche semantique",
            "semantic search",
        ]

        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break

        return cleaned.strip(" :,-")
