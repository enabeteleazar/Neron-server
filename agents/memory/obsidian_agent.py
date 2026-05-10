from memory.obsidian.client import ObsidianMemory


class ObsidianAgent:
    def __init__(self, vault_path: str):
        self.memory = ObsidianMemory(vault_path)

    def handle(self, text: str) -> dict:
        lowered = text.lower().strip()

        if self._is_write_intent(lowered):
            content = self._clean_write_text(text)

            if not content:
                return {
                    "response": "Je n’ai pas de contenu à enregistrer.",
                    "intent": "memory_write",
                    "agent": "obsidian_agent",
                    "error": "empty_content"
                }

            title = content[:60]

            path = self.memory.write_note(
                folder="Ideas",
                title=title,
                content=content,
                tags=["idee", "neron", "obsidian"]
            )

            return {
                "response": f"Idée enregistrée dans Obsidian : {path}",
                "intent": "memory_write",
                "agent": "obsidian_agent",
                "error": None
            }

        if self._is_search_intent(lowered):
            query = self._clean_search_text(text)

            if not query:
                return {
                    "response": "Quelle information dois-je chercher dans Obsidian ?",
                    "intent": "memory_search",
                    "agent": "obsidian_agent",
                    "error": "empty_query"
                }

            results = self.memory.search(query)

            if not results:
                return {
                    "response": "Je n’ai rien trouvé dans la mémoire Obsidian.",
                    "intent": "memory_search",
                    "agent": "obsidian_agent",
                    "error": None
                }

            formatted = "\n".join(
                f"- {result['title']} : {result['file']}"
                for result in results
            )

            return {
                "response": f"Résultats trouvés dans Obsidian :\n{formatted}",
                "intent": "memory_search",
                "agent": "obsidian_agent",
                "error": None
            }

        return {
            "response": "Je n’ai pas compris l’action mémoire demandée.",
            "intent": "memory_unknown",
            "agent": "obsidian_agent",
            "error": "unknown_memory_action"
        }

    def _is_write_intent(self, text: str) -> bool:
        keywords = [
            "idée",
            "ajoute une idée",
            "note ceci",
            "mémorise",
            "memorise",
            "sauvegarde ceci",
            "retient ceci",
            "enregistre ceci"
        ]
        return any(keyword in text for keyword in keywords)

    def _is_search_intent(self, text: str) -> bool:
        keywords = [
            "cherche dans obsidian",
            "recherche mémoire",
            "cherche dans la mémoire",
            "retrouve mes notes",
            "recherche dans obsidian",
            "mémoire obsidian"
        ]
        return any(keyword in text for keyword in keywords)

    def _clean_write_text(self, text: str) -> str:
        replacements = [
            "ajoute une idée",
            "idée",
            "note ceci",
            "mémorise",
            "memorise",
            "sauvegarde ceci",
            "retient ceci",
            "enregistre ceci"
        ]

        cleaned = text.strip()

        for item in replacements:
            cleaned = cleaned.replace(item, "", 1)
            cleaned = cleaned.replace(item.capitalize(), "", 1)

        return cleaned.strip(" :,-")

    def _clean_search_text(self, text: str) -> str:
        cleaned = text.lower().strip()

        prefixes = [
            "cherche dans obsidian",
            "recherche mémoire",
            "cherche dans la mémoire",
            "retrouve mes notes",
            "recherche dans obsidian",
            "mémoire obsidian"
        ]

        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break

        return cleaned.strip(" :,-")
