# modules/neron_llm/tests/test_models.py

"""
Tests unitaires pour les modèles Pydantic
"""

import pytest
from pydantic import ValidationError
import sys
from pathlib import Path

# Ajouter le path si nécessaire
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from models import (
    PromptRequest,
    LLMResponse,
    HealthResponse,
    ErrorResponse,
    ModelListResponse
)


class TestPromptRequest:
    """Tests pour le modèle PromptRequest"""
    
    def test_minimal_prompt_request(self):
        """Test avec les champs minimaux requis"""
        request = PromptRequest(prompt="Test prompt")
        
        assert request.prompt == "Test prompt"
        assert request.model == "llama3.2:1b"  # Valeur par défaut
        assert request.temperature == 0.7
        assert request.max_tokens == 2048
        assert request.system_prompt is None
        assert request.context is None
    
    def test_full_prompt_request(self):
        """Test avec tous les champs"""
        request = PromptRequest(
            prompt="Test prompt",
            model="mistral",
            temperature=0.9,
            max_tokens=1024,
            system_prompt="Tu es un assistant.",
            context=["msg1", "msg2"]
        )
        
        assert request.prompt == "Test prompt"
        assert request.model == "mistral"
        assert request.temperature == 0.9
        assert request.max_tokens == 1024
        assert request.system_prompt == "Tu es un assistant."
        assert request.context == ["msg1", "msg2"]
    
    def test_missing_prompt(self):
        """Test sans le champ obligatoire prompt"""
        with pytest.raises(ValidationError) as exc_info:
            PromptRequest()
        
        assert "prompt" in str(exc_info.value)
    
    def test_invalid_temperature_too_low(self):
        """Test avec température trop basse"""
        with pytest.raises(ValidationError):
            PromptRequest(
                prompt="Test",
                temperature=-0.1
            )
    
    def test_invalid_temperature_too_high(self):
        """Test avec température trop haute"""
        with pytest.raises(ValidationError):
            PromptRequest(
                prompt="Test",
                temperature=2.1
            )
    
    def test_invalid_max_tokens_too_low(self):
        """Test avec max_tokens trop bas"""
        with pytest.raises(ValidationError):
            PromptRequest(
                prompt="Test",
                max_tokens=0
            )
    
    def test_invalid_max_tokens_too_high(self):
        """Test avec max_tokens trop haut"""
        with pytest.raises(ValidationError):
            PromptRequest(
                prompt="Test",
                max_tokens=10000
            )


class TestLLMResponse:
    """Tests pour le modèle LLMResponse"""
    
    def test_minimal_llm_response(self):
        """Test avec les champs minimaux"""
        response = LLMResponse(
            response="Test response",
            model="llama3.2:1b"
        )
        
        assert response.response == "Test response"
        assert response.model == "llama3.2:1b"
        assert response.tokens_used is None
        assert response.generation_time is None
    
    def test_full_llm_response(self):
        """Test avec tous les champs"""
        response = LLMResponse(
            response="Test response",
            model="llama3.2:1b",
            tokens_used=42,
            generation_time=1.5
        )
        
        assert response.response == "Test response"
        assert response.model == "llama3.2:1b"
        assert response.tokens_used == 42
        assert response.generation_time == 1.5
    
    def test_missing_required_fields(self):
        """Test sans champs obligatoires"""
        with pytest.raises(ValidationError):
            LLMResponse(response="Test")
        
        with pytest.raises(ValidationError):
            LLMResponse(model="llama3.2:1b")


class TestHealthResponse:
    """Tests pour le modèle HealthResponse"""
    
    def test_minimal_health_response(self):
        """Test avec les champs minimaux"""
        response = HealthResponse(
            status="healthy",
            service="Neron_LLM",
            version="1.0.0",
            ollama_connected=True
        )
        
        assert response.status == "healthy"
        assert response.service == "Neron_LLM"
        assert response.version == "1.0.0"
        assert response.ollama_connected is True
        assert response.available_models is None
    
    def test_full_health_response(self):
        """Test avec tous les champs"""
        response = HealthResponse(
            status="healthy",
            service="Neron_LLM",
            version="1.0.0",
            ollama_connected=True,
            available_models=["llama3.2:1b", "mistral"]
        )
        
        assert response.available_models == ["llama3.2:1b", "mistral"]


class TestErrorResponse:
    """Tests pour le modèle ErrorResponse"""
    
    def test_minimal_error_response(self):
        """Test avec les champs minimaux"""
        response = ErrorResponse(
            error="An error occurred",
            status_code=500
        )
        
        assert response.error == "An error occurred"
        assert response.status_code == 500
        assert response.detail is None
    
    def test_full_error_response(self):
        """Test avec tous les champs"""
        response = ErrorResponse(
            error="An error occurred",
            detail="Detailed error message",
            status_code=500
        )
        
        assert response.error == "An error occurred"
        assert response.detail == "Detailed error message"
        assert response.status_code == 500


class TestModelListResponse:
    """Tests pour le modèle ModelListResponse"""
    
    def test_model_list_response(self):
        """Test de la liste des modèles"""
        models = [
            {"name": "llama3.2:1b", "size": 1234567890},
            {"name": "mistral", "size": 9876543210}
        ]
        
        response = ModelListResponse(models=models)
        
        assert len(response.models) == 2
        assert response.models[0]["name"] == "llama3.2:1b"
        assert response.models[1]["name"] == "mistral"
    
    def test_empty_model_list(self):
        """Test avec une liste vide"""
        response = ModelListResponse(models=[])
        
        assert response.models == []
    
    def test_missing_models_field(self):
        """Test sans le champ models"""
        with pytest.raises(ValidationError):
            ModelListResponse()
