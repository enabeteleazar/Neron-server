"""LLM provider adapters
Ce module expose une interface stable pour appeler différents providers (ollama, claude, etc.)
"""

try:
    from core.llm_client.client import NéronLLMClient
except Exception:
    NéronLLMClient = None

# Fallback singleton
_client = None

def _get_client():
    global _client
    if _client is None and NéronLLMClient is not None:
        try:
            _client = NéronLLMClient()
        except Exception:
            _client = None
    return _client


async def call_llm(prompt: str, task_type: str = "chat", **kwargs):
    client = _get_client()
    if client is None:
        raise RuntimeError("LLM client unavailable")
    # delegate to client's generate
    return await client.generate(task_type=task_type, prompt=prompt, context=kwargs.get("context"))
