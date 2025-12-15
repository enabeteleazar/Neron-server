import subprocess
from neron_llm.config import MODEL_NAME, MAX_TOKENS, TEMPERATURE
from neron_llm.state import LLM_STATE, CURRENT_MODEL, LAST_RESPONSE, PROMPT

class LLMCore:
    def __init__(self):
        self.model_name = MODEL_NAME
        self.max_tokens = MAX_TOKENS
        self.temperature = TEMPERATURE
        self.state = LLM_STATE
        self.current_model = CURRENT_MODEL
        self.last_response = LAST_RESPONSE
        self.prompt_count = PROMPT

    def load_model(self):
        # Logic to load the model
        self.state = "loading_model"
        # Simulate model loading
        self.current_model = self.model_name
        self.state = "ready"

    def generate(self, prompt: str) -> str:
        result = subprocess.run(
            ["ollama", "generate", self.model_name, prompt],
            capture_output=True,
            text=True
        )
        if self.state != "ready":
            raise Exception("Model is not ready")
        
        self.state = "busy"
        self.prompt_count += 1
        
        # Simulate response generation
        response = f"Generated response for prompt: {prompt}"
        
        self.last_response = response
        self.state = "ready"
        
        return result.stdout.strip()