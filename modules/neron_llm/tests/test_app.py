# modules/neron_llm/tests/test_app.py

"""
Tests unitaires pour l'application FastAPI
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import sys
from pathlib import Path

# Ajouter le répertoire parent pour les imports
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


@pytest.fixture
def mock_ollama_client_instance(mock_httpx_client):
    """Mock de l'instance OllamaClient utilisée par l'app"""
    mock_instance = MagicMock()
    
    # Mock de la méthode generate
    mock_instance.generate = AsyncMock(return_value={
        "response": "Réponse de test",
        "model": "llama3.2:1b",
        "tokens_used": 42,
        "generation_time": 1.5
    })
    
    # Mock de la méthode list_models
    mock_instance.list_models = AsyncMock(return_value=[
        {"name": "llama3.2:1b", "size": 1234567890}
    ])
    
    # Mock de la méthode check_connection
    mock_instance.check_connection = AsyncMock(return_value=True)
    
    # Mock de close
    mock_instance.close = AsyncMock()
    
    return mock_instance


@pytest.fixture
def client(mock_ollama_client_instance):
    """Fixture pour le client de test FastAPI"""
    # Patcher le module ollama_client avant d'importer l'app
    with patch('ollama_client.OllamaClient', return_value=mock_ollama_client_instance):
        # Importer l'app après avoir patché
        from app import app
        
        # Patcher la variable globale ollama_client dans app
        import app as app_module
        app_module.ollama_client = mock_ollama_client_instance
        
        with TestClient(app) as test_client:
            yield test_client


def test_root_endpoint(client):
    """Test l'endpoint racine"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "service" in data
    assert data["service"] == "Néron LLM Service"
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"
    assert "endpoints" in data


def test_health_check_success(client, mock_ollama_client_instance):
    """Test le health check avec connexion OK"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "service" in data
    assert data["service"] == "Neron_LLM"
    assert "version" in data
    assert data["version"] == "1.0.0"
    assert "ollama_connected" in data
    assert data["ollama_connected"] is True


def test_health_check_degraded(client, mock_ollama_client_instance):
    """Test le health check avec connexion en échec"""
    # Modifier le mock pour retourner False
    mock_ollama_client_instance.check_connection = AsyncMock(return_value=False)
    
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "degraded"
    assert data["ollama_connected"] is False


def test_list_models_success(client, mock_ollama_client_instance):
    """Test la liste des modèles"""
    response = client.get("/models")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "models" in data
    assert isinstance(data["models"], list)
    assert len(data["models"]) > 0


def test_list_models_error(client, mock_ollama_client_instance):
    """Test la gestion d'erreur lors de la liste des modèles"""
    # Configurer le mock pour lever une exception
    mock_ollama_client_instance.list_models = AsyncMock(side_effect=Exception("Connection error"))
    
    response = client.get("/models")
    
    assert response.status_code == 503


def test_ask_endpoint_success(client, mock_ollama_client_instance):
    """Test la génération de réponse avec succès"""
    payload = {
        "prompt": "Bonjour",
        "model": "llama3.2:1b"
    }
    
    response = client.post("/ask", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data
    assert "model" in data
    assert data["response"] == "Réponse de test"
    assert data["model"] == "llama3.2:1b"
    assert "tokens_used" in data
    assert "generation_time" in data


def test_ask_endpoint_with_all_options(client, mock_ollama_client_instance):
    """Test avec toutes les options disponibles"""
    payload = {
        "prompt": "Test prompt",
        "model": "llama3.2:1b",
        "temperature": 0.9,
        "max_tokens": 1024,
        "system_prompt": "Tu es un assistant utile.",
        "context": ["message1", "message2"]
    }
    
    response = client.post("/ask", json=payload)
    
    assert response.status_code == 200
    
    # Vérifier que generate a été appelé avec les bons paramètres
    mock_ollama_client_instance.generate.assert_called_once()
    call_kwargs = mock_ollama_client_instance.generate.call_args[1]
    
    assert call_kwargs["prompt"] == "Test prompt"
    assert call_kwargs["model"] == "llama3.2:1b"
    assert call_kwargs["temperature"] == 0.9
    assert call_kwargs["max_tokens"] == 1024
    assert call_kwargs["system_prompt"] == "Tu es un assistant utile."
    assert call_kwargs["context"] == ["message1", "message2"]


def test_ask_endpoint_missing_prompt(client):
    """Test avec prompt manquant (validation Pydantic)"""
    payload = {
        "model": "llama3.2:1b"
    }
    
    response = client.post("/ask", json=payload)
    
    # Erreur de validation Pydantic
    assert response.status_code == 422


def test_ask_endpoint_invalid_temperature(client):
    """Test avec température invalide"""
    payload = {
        "prompt": "Test",
        "temperature": 3.0  # > 2.0 (max)
    }
    
    response = client.post("/ask", json=payload)
    
    # Erreur de validation Pydantic
    assert response.status_code == 422


def test_ask_endpoint_server_error(client, mock_ollama_client_instance):
    """Test la gestion d'erreur serveur"""
    # Configurer le mock pour lever une exception
    mock_ollama_client_instance.generate = AsyncMock(side_effect=Exception("Ollama error"))
    
    payload = {
        "prompt": "Test",
        "model": "llama3.2:1b"
    }
    
    response = client.post("/ask", json=payload)
    
    assert response.status_code == 500
    data = response.json()
    
    assert "error" in data


def test_generate_endpoint_alias(client, mock_ollama_client_instance):
    """Test que /generate est un alias de /ask"""
    payload = {
        "prompt": "Test",
        "model": "llama3.2:1b"
    }
    
    response = client.post("/generate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data


def test_ask_with_default_model(client, mock_ollama_client_instance):
    """Test avec le modèle par défaut"""
    payload = {
        "prompt": "Test"
        # model non spécifié
    }
    
    response = client.post("/ask", json=payload)
    
    assert response.status_code == 200
    
    # Vérifier que le modèle par défaut a été utilisé
    call_kwargs = mock_ollama_client_instance.generate.call_args[1]
    assert call_kwargs["model"] == "llama3.2:1b"


def test_concurrent_requests(client, mock_ollama_client_instance):
    """Test des requêtes concurrentes"""
    import concurrent.futures
    
    def make_request():
        payload = {"prompt": "Test", "model": "llama3.2:1b"}
        return client.post("/ask", json=payload)
    
    # Faire 5 requêtes en parallèle
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # Vérifier que toutes ont réussi
    assert all(r.status_code == 200 for r in results)
    assert mock_ollama_client_instance.generate.call_count == 5
