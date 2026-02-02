import pytest
import requests

OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:1b"  # <- modèle réel disponible

@pytest.mark.ollama
def test_ollama_container_up():
    """Vérifie que le conteneur Ollama répond"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/v1/models", timeout=5)
        assert response.status_code == 200
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Conteneur Ollama non disponible: {e}")

@pytest.mark.ollama
def test_ollama_models():
    """Vérifie que le modèle par défaut est disponible"""
    response = requests.get(f"{OLLAMA_HOST}/v1/models", timeout=5)
    models = response.json()["data"]  # <- correction ici
    model_ids = [m["id"] for m in models]
    assert DEFAULT_MODEL in model_ids, f"Le modèle {DEFAULT_MODEL} n'est pas disponible"

@pytest.mark.ollama
def test_ollama_prompt():
    """Teste une requête simple pour valider l'inférence"""
    payload = {
        "model": DEFAULT_MODEL,
        "prompt": "Bonjour Ollama, réponds-moi simplement : 1+1=?"
    }
    response = requests.post(
        f"{OLLAMA_HOST}/v1/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    assert response.status_code == 200, f"Erreur lors de l'appel à l'API Ollama: {response.text}"
    data = response.json()
    assert "choices" in data or "completion" in data, "La réponse ne contient pas de texte"
