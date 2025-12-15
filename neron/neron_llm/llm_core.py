# neron_llm/llm_core.py
import subprocess
from neron_llm.config import MODEL_NAME
from neron_llm.state import LLM_STATUS, CURRENT_MODEL, LAST_RESPONSE, PROMPT_COUNT

class LLMCore:
    def __init__(self, model_name=MODEL_NAME):
        global LLM_STATUS, CURRENT_MODEL
        self.model_name = model_name
        CURRENT_MODEL = model_name
        LLM_STATUS = "loading_model"

        # Vérifie que le modèle est disponible
        if not self._check_model():
            LLM_STATUS = "error"
            raise RuntimeError(f"Modèle {model_name} non trouvé ou Ollama non installé.")
        LLM_STATUS = "ready"

    def _check_model(self) -> bool:
        """Vérifie si le modèle est disponible dans Ollama."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True
            )
            models = result.stdout.strip().splitlines()
            return any(self.model_name in m for m in models)
        except Exception:
            return False

    def generate(self, prompt: str) -> str:
        """Génère une réponse à partir du prompt via Ollama local."""
        global LLM_STATUS, LAST_RESPONSE, PROMPT_COUNT
        LLM_STATUS = "busy"
        try:
            result = subprocess.run(
                ["ollama", "generate", self.model_name, prompt],
                capture_output=True,
                text=True
            )
            response = result.stdout.strip()
            LAST_RESPONSE = response
            PROMPT_COUNT += 1
            LLM_STATUS = "ready"
            return response
        except Exception as e:
            LLM_STATUS = "error"
            return f"Erreur génération LLM : {e}"

# Test rapide
if __name__ == "__main__":
    llm = LLMCore()
    response = llm.generate("Bonjour Néron, peux-tu te présenter ?")
    print("Réponse LLM :", response)
    print("Statut :", LLM_STATUS)
    print("Nombre de prompts traités :", PROMPT_COUNT)