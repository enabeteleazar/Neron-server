# modules/neron_llm/tests/test_ollama_client.py

"""
Tests unitaires pour le client Ollama
"""

import pytest
from unittest.mock import patch, AsyncMock
import httpx
import sys
from pathlib import Path

# Ajouter le path si nécessaire
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from ollama_client import OllamaClient


@pytest.mark.asyncio
async def test_ollama_client_initialization():
    """Test l'initialisation du client"""
    client = OllamaClient(
        host="http://localhost:11434",
        timeout=60.0
    )
    
    assert client.host == "http://localhost:11434"
    assert client.timeout == 60.0
    assert client.client is not None
    
    await client.close()


@pytest.mark.asyncio
async def test_generate_success(mock_httpx_client, mock_ollama_response):
    """Test la génération d'une réponse avec succès"""
    with patch('httpx.AsyncClient', return_value=mock_httpx_client):
        client = OllamaClient()
        
        result = await client.generate(
            prompt="Test prompt",
            model="llama3.2:1b"
        )
        
        assert "response" in result
        assert result["response"] == mock_ollama_response["response"]
        assert result["model"] == "llama3.2:1b"
        assert "tokens_used" in result
        assert "generation_time" in result
        
        await client.close()


@pytest.mark.asyncio
async def test_generate_with_options(mock_httpx_client):
    """Test la génération avec options (temperature, max_tokens, etc.)"""
    with patch('httpx.AsyncClient', return_value=mock_httpx_client):
        client = OllamaClient()
        
        result = await client.generate(
            prompt="Test prompt",
            model="llama3.2:1b",
            temperature=0.9,
            max_tokens=1024,
            system_prompt="Tu es un assistant utile."
        )
        
        # Vérifier que la requête a été faite
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        
        # Vérifier l'URL
        assert call_args[0][0].endswith("/api/generate")
        
        # Vérifier le payload
        payload = call_args[1]["json"]
        assert payload["prompt"] == "Test prompt"
        assert payload["model"] == "llama3.2:1b"
        assert payload["system"] == "Tu es un assistant utile."
        assert payload["options"]["temperature"] == 0.9
        assert payload["options"]["num_predict"] == 1024
        
        await client.close()


@pytest.mark.asyncio
async def test_generate_with_context(mock_httpx_client):
    """Test la génération avec contexte de conversation"""
    with patch('httpx.AsyncClient', return_value=mock_httpx_client):
        client = OllamaClient()
        
        context = ["message1", "message2"]
        
        result = await client.generate(
            prompt="Test prompt",
            context=context
        )
        
        # Vérifier le payload
        call_args = mock_httpx_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["context"] == context
        
        await client.close()


@pytest.mark.asyncio
async def test_list_models_success(mock_httpx_client, mock_ollama_models):
    """Test la récupération de la liste des modèles"""
    with patch('httpx.AsyncClient', return_value=mock_httpx_client):
        client = OllamaClient()
        
        models = await client.list_models()
        
        assert isinstance(models, list)
        assert len(models) == 2
        assert models[0]["name"] == "llama3.2:1b"
        assert models[1]["name"] == "mistral:latest"
        
        await client.close()


@pytest.mark.asyncio
async def test_list_models_error(mock_httpx_client):
    """Test la gestion d'erreur lors de la récupération des modèles"""
    # Configurer le mock pour lever une exception
    mock_httpx_client.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
    
    with patch('httpx.AsyncClient', return_value=mock_httpx_client):
        client = OllamaClient()
        
        models = await client.list_models()
        
        # Doit retourner une liste vide en cas d'erreur
        assert models == []
        
        await client.close()


@pytest.mark.asyncio
async def test_check_connection_success(mock_httpx_client):
    """Test la vérification de connexion réussie"""
    with patch('httpx.AsyncClient', return_value=mock_httpx_client):
        client = OllamaClient()
        
        connected = await client.check_connection()
        
        assert connected is True
        
        await client.close()


@pytest.mark.asyncio
async def test_check_connection_failure(mock_httpx_client):
    """Test la vérification de connexion en échec"""
    # Configurer le mock pour retourner un statut d'erreur
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_httpx_client.get = AsyncMock(return_value=mock_response)
    
    with patch('httpx.AsyncClient', return_value=mock_httpx_client):
        client = OllamaClient()
        
        connected = await client.check_connection()
        
        assert connected is False
        
        await client.close()


@pytest.mark.asyncio
async def test_generate_http_error(mock_httpx_client):
    """Test la gestion d'erreur HTTP lors de la génération"""
    # Configurer le mock pour lever une exception HTTP
    mock_httpx_client.post = AsyncMock(side_effect=httpx.HTTPError("Server error"))
    
    with patch('httpx.AsyncClient', return_value=mock_httpx_client):
        client = OllamaClient()
        
        with pytest.raises(httpx.HTTPError):
            await client.generate(prompt="Test")
        
        await client.close()


@pytest.mark.asyncio
async def test_close_client(mock_httpx_client):
    """Test la fermeture du client"""
    with patch('httpx.AsyncClient', return_value=mock_httpx_client):
        client = OllamaClient()
        
        await client.close()
        
        # Vérifier que aclose a été appelé
        mock_httpx_client.aclose.assert_called_once()
