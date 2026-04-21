# modules/neron_llm/ollama_client.py

"""
Client HTTP pour communiquer avec Ollama
"""

import httpx
import logging
from typing import Optional, List, Dict, Any

try:
    from config import settings
except ImportError:
    from .config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Client pour communiquer avec le service Ollama via HTTP
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """
        Initialise le client Ollama
        
        Args:
            host: URL du serveur Ollama (par défaut depuis config)
            timeout: Timeout pour les requêtes (par défaut depuis config)
        """
        self.host = host or settings.OLLAMA_HOST
        self.timeout = timeout or settings.OLLAMA_TIMEOUT
        self.client = httpx.AsyncClient(timeout=self.timeout)
        
        logger.info(f"OllamaClient initialisé: {self.host}")
    
    async def generate(
        self,
        prompt: str,
        model: str = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Génère une réponse à partir d'un prompt
        
        Args:
            prompt: Le texte du prompt
            model: Modèle à utiliser
            system_prompt: Prompt système optionnel
            temperature: Température de génération
            max_tokens: Nombre maximum de tokens
            context: Historique de conversation
            
        Returns:
            Dict contenant la réponse et les métadonnées
            
        Raises:
            httpx.HTTPError: Si la requête échoue
        """
        model = model or settings.DEFAULT_MODEL
        
        # Construction du payload
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        # Options additionnelles
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
            
        if options:
            payload["options"] = options
        
        # Ajout du system prompt
        if system_prompt:
            payload["system"] = system_prompt
        
        # Ajout du contexte
        if context:
            payload["context"] = context
        
        logger.debug(f"Envoi du prompt au modèle {model}")
        
        try:
            response = await self.client.post(
                f"{self.host}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"Réponse reçue du modèle {model}")
            
            return {
                "response": data.get("response", ""),
                "model": model,
                "tokens_used": data.get("eval_count"),
                "generation_time": data.get("total_duration", 0) / 1e9  # Conversion en secondes
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Erreur lors de la génération: {e}")
            raise
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Liste les modèles disponibles sur Ollama
        
        Returns:
            Liste des modèles avec leurs informations
        """
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            
            data = response.json()
            return data.get("models", [])
            
        except httpx.HTTPError as e:
            logger.error(f"Erreur lors de la récupération des modèles: {e}")
            return []
    
    async def check_connection(self) -> bool:
        """
        Vérifie la connexion à Ollama
        
        Returns:
            True si la connexion est établie, False sinon
        """
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Impossible de se connecter à Ollama: {e}")
            return False
    
    async def close(self):
        """Ferme le client HTTP"""
        await self.client.aclose()
        logger.info("OllamaClient fermé")
