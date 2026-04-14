from neron_llm.core.router import LLMRouter
from neron_llm.providers.ollama import OllamaProvider
from neron_llm.providers.claude import ClaudeProvider
from neron_llm.core.types import LLMRequest


class LLMManager:

    def __init__(self):
        self.router = LLMRouter()

        self.providers = {
            "ollama": OllamaProvider(),
            "claude": ClaudeProvider()
        }

    def handle(self, request: LLMRequest):

        provider_name = self.router.select_provider(request)
        model = self.router.select_model(request.task)

        provider = self.providers.get(provider_name)

        if not provider:
            provider = self.providers["ollama"]

        response = provider.generate(request, model)

        return {
            "provider": provider_name,
            "model": model,
            "response": response
        }
