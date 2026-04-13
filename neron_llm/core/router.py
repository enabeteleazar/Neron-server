class LLMRouter:

    def select_provider(self, request):
        task = request.task or "default"

        if task == "code":
            return "claude"
        return "ollama"

    def select_model(self, request):
        task = request.task or "default"

        if task == "code":
            return "deepseek-coder"
        return "mistral"
