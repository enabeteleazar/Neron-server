from memory.obsidian.client import ObsidianMemory


class ObsidianAgent:
    def __init__(self, vault_path: str):
        self.memory = ObsidianMemory(vault_path)

    def handle(self, text: str) -> dict:
        lowered = text.lower()

        if lowered.startswith("idée") or "ajoute une idée" in lowered:
            clean = text.replace("idée", "", 1).strip()
            path = self.memory.write_note(
                folder="Ideas",
                title=clean[:60] or "Nouvelle idée",
                content=clean,
                tags=["idee", "neron"]
            )

            return {
                "response": f"Idée enregistrée dans Obsidian : {path}",
                "intent": "memory_write",
                "agent": "obsidian_agent"
            }

        if "recherche mémoire" in lowered or "cherche dans obsidian" in lowered:
            query = (
                text.replace("recherche mémoire", "")
                    .replace("cherche dans obsidian", "")
                    .strip()
            )

            results = self.memory.search(query)

            if not results:
                return {
                    "response": "Je n’ai rien trouvé dans la mémoire Obsidian.",
                    "intent": "memory_search",
                    "agent": "obsidian_agent"
                }

            formatted = "\n".join(
                f"- {r['title']} : {r['file']}" for r in results
            )

            return {
                "response": f"Résultats trouvés :\n{formatted}",
                "intent": "memory_search",
                "agent": "obsidian_agent"
            }

        return {
            "response": "Je n’ai pas compris l’action mémoire demandée.",
            "intent": "memory_unknown",
            "agent": "obsidian_agent"
        }
