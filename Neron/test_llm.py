from neron_llm.prompt_handler import PromptHandler

handler = PromptHandler()
prompt = handler.build_prompt("Bonjour Néron, peux tu te présenter ?")
response = handler.extract_response(prompt, "Néron est un assistant virtuel développé par Homebox.")

print("Prompt:", prompt)
print("Response:", response)