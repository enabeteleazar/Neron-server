# modules/neron_llm/config.py

"""
Configuration pour le service Néron LLM
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Configuration du service LLM"""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Environnement
    ENV: str = "production"
    
    # API Service
    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 5000
    
    # Ollama Configuration
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: float = 300.0
    
    # Modèle par défaut
    DEFAULT_MODEL: str = "llama3.2:1b"
    
    # Limites
    MAX_TOKENS: int = 2048
    TEMPERATURE: float = 0.7
    
    # Logging
    LOG_LEVEL: str = "INFO"


# Instance globale
settings = Settings()
