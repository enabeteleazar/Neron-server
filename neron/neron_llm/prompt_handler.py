from neron_llm.llm_manager import LLMManagerWrapper

class PromptHandler:
    def __init__(self):
        self.llm_manager = LLMManagerWrapper()
        self.llm_manager.load_model()

    def handle_prompt(self, prompt: str) -> str:
        response = self.llm_manager.generate_response(prompt)
        return response

# Test rapide
if __name__ == "__main__": 
    handler = PromptHandler()
    resp = handler.handle_prompt("Bonjour néron, Comment ça va ?")
    print("Réponse :", resp)

