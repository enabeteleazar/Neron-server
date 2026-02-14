import requests

# Adresse de ton Néron-LLM
LLM_URL = "http://localhost:11434/v1/completions"

# Prompt de test
prompt = "Bonjour Néron,  que puis-je faire ?"

# Payload pour la requête
data = {
    "model": "llama3.2:1B",
    "prompt": prompt,
    "max_tokens": 100
}

try:
    response = requests.post(LLM_URL, json=data)
    response.raise_for_status()
    result = response.json()
    print("Réponse Néron-LLM :")
    print(result)
except Exception as e:
    print("Erreur lors de la requête vers Néron-LLM :", e)
