from neron_llm.core.router import LLMRouter
from neron_llm.providers.ollama import OllamaProvider
from neron_llm.providers.claude import ClaudeProvider


class LLMManager:

    def __init__(self):
        self.router = LLMRouter()
        self.providers = {
            "ollama": OllamaProvider(),
            "claude": ClaudeProvider()
        }

    async def generate(self, request):
        provider_name = self.router.select_provider(request)
        provider = self.providers[provider_name]

        result = await provider.generate(request.message)

        return {
            "provider": provider_name,
            "response": result
        }
