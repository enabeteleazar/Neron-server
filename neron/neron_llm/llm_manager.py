from neron_llm.llm_core import LLMCore  
from neron_llm.llm_manager import LLMManager
from neron_llm.state import LLM_STATE

class LLMManagerWrapper:
    def __init__(self):
        self.llm_core = LLMCore()
        self.llm_manager = LLMManager(self.llm_core)

    def load_model(self):
        self.llm_manager.load_model()

    def generate_response(self, prompt: str) -> str:
        return self.llm_manager.generate_response(prompt)

    def get_state(self) -> str:
        return self.llm_core.state