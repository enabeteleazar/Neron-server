from neron_llm.llm_core import LLMCore  
from neron_llm.state import LLM_STATE

class LLMManager:
    def __init__(self, model_name="llama3.2"):
        self.llm = LLMCore(model_name=model_name)

    def ask(self, prompt: str) -> str:
        return self.llm.generate(prompt)

    def load_model(self):
        self.llm_manager.load_model()

    def generate_response(self, prompt: str) -> str:
        return self.llm_manager.generate_response(prompt)

    def get_state(self) -> str:
        return self.llm_core.state