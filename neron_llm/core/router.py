from neron_llm.config import get_llm_config
from neron_llm.core.types import LLMRequest


class LLMRouter:
    """Sélectionne le modèle et le provider en fonction de la tâche et de la config YAML.

    Section attendue dans neron.yaml :
        llm:
          model: llama3.2:1b          # modèle par défaut
          fallback_model: llama3.2:1b
          host: http://localhost:11434
          timeout: 120
          model_map:
            code: deepseek-coder:latest
            summary: llama3.2:1b
            default: llama3.2:1b
    """

    def __init__(self):
        cfg = get_llm_config()
        self.model_map: dict = cfg.get("model_map", {})
        self.default_model: str = cfg.get("model") or self.model_map.get("default", "llama3.2:1b")
        self.fallback_model: str = cfg.get("fallback_model", self.default_model)

    def select_model(self, task: str | None) -> str:
        if not task or task == "default":
            return self.default_model
        return self.model_map.get(task, self.default_model)

    def select_provider(self, request: LLMRequest) -> str:
        """Retourne le nom du provider à utiliser.

        Priorité : champ explicite > config > ollama par défaut.
        """
        if request.provider:
            return request.provider
        cfg = get_llm_config()
        return cfg.get("default_provider", "ollama")
