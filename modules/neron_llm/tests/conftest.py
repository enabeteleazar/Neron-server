# modules/neron_llm/tests/conftest.py

"""
Configuration pytest et fixtures partagées
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH pour les imports
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


@pytest.fixture
def mock_ollama_response():
    """Fixture pour une réponse Ollama standard"""
    return {
        "response": "Ceci est une réponse de test",
        "model": "llama3.2:1b",
        "eval_count": 42,
        "total_duration": 1500000000  # 1.5 secondes en nanosecondes
    }


@pytest.fixture
def mock_ollama_models():
    """Fixture pour la liste des modèles Ollama"""
    return {
        "models": [
            {
                "name": "llama3.2:1b",
                "size": 1234567890,
                "digest": "abc123def456",
                "modified_at": "2024-01-01T00:00:00Z"
            },
            {
                "name": "mistral:latest",
                "size": 9876543210,
                "digest": "xyz789uvw012",
                "modified_at": "2024-01-02T00:00:00Z"
            }
        ]
    }


@pytest.fixture
def mock_httpx_client(mock_ollama_response, mock_ollama_models):
    """Mock du client httpx"""
    mock_client = MagicMock()
    
    # Mock pour la méthode post (génération)
    mock_post_response = AsyncMock()
    mock_post_response.status_code = 200
    mock_post_response.json.return_value = mock_ollama_response
    mock_post_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_post_response)
    
    # Mock pour la méthode get (liste des modèles et health)
    mock_get_response = AsyncMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = mock_ollama_models
    mock_client.get = AsyncMock(return_value=mock_get_response)
    
    # Mock pour aclose
    mock_client.aclose = AsyncMock()
    
    return mock_client
