from neron_llm.config import get_llm_config


class LLMRouter:
    def __init__(self):
        cfg = get_llm_config()

        self.model_map = cfg.get("model_map", {})
        self.default_model = cfg.get("model") or self.model_map.get("default")
        self.fallback_model = cfg.get("fallback_model", self.default_model)

    def select_model(self, task: str | None):
        if not task:
            return self.default_model

        return self.model_map.get(task, self.default_model)

    def select_provider(self, request):
        # extension future (claude / ollama priority)
        return request.provider or "ollama"
