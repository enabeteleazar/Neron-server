# modules/neron_llm/app.py

"""
Service FastAPI pour Néron LLM
Wrapper autour d'Ollama
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

try:
    from config import settings
    from models import (
        PromptRequest,
        LLMResponse,
        HealthResponse,
        ErrorResponse,
        ModelListResponse
    )
    from ollama_client import OllamaClient
except ImportError:
    from .config import settings
    from .models import (
        PromptRequest,
        LLMResponse,
        HealthResponse,
        ErrorResponse,
        ModelListResponse
    )
    from .ollama_client import OllamaClient

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Instance du client Ollama (sera initialisée au startup)
ollama_client: OllamaClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    global ollama_client
    
    # Startup
    logger.info("🚀 Démarrage du service Néron LLM")
    ollama_client = OllamaClient()
    
    # Vérification de la connexion à Ollama
    connected = await ollama_client.check_connection()
    if connected:
        logger.info("✅ Connexion à Ollama établie")
    else:
        logger.warning("⚠️ Impossible de se connecter à Ollama")
    
    yield
    
    # Shutdown
    logger.info("🛑 Arrêt du service Néron LLM")
    await ollama_client.close()


# FastAPI app
app = FastAPI(
    title="Néron LLM Service",
    description="Service de wrapper pour Ollama - Néron AI Assistant",
    version="1.0.0",
    lifespan=lifespan
)


# ----------------------------
# Exception handlers
# ----------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Gestionnaire d'exceptions HTTP"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Gestionnaire d'exceptions générales"""
    logger.error(f"Erreur non gérée: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            status_code=500
        ).dict()
    )


# ----------------------------
# Endpoints
# ----------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Vérifie l'état du service et de la connexion à Ollama
    """
    connected = await ollama_client.check_connection()
    
    response_data = {
        "status": "healthy" if connected else "degraded",
        "service": "Neron_LLM",
        "version": "1.0.0",
        "ollama_connected": connected
    }
    
    # Optionnel: récupérer la liste des modèles
    if connected:
        try:
            models = await ollama_client.list_models()
            response_data["available_models"] = [m.get("name") for m in models]
        except Exception as e:
            logger.warning(f"Impossible de récupérer les modèles: {e}")
    
    return response_data


@app.get("/models", response_model=ModelListResponse)
async def list_models():
    """
    Liste tous les modèles disponibles sur Ollama
    """
    try:
        models = await ollama_client.list_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des modèles: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Impossible de récupérer les modèles depuis Ollama"
        )


@app.post("/ask", response_model=LLMResponse)
async def ask(request: PromptRequest):
    """
    Génère une réponse à partir d'un prompt
    
    Args:
        request: Requête contenant le prompt et les options
        
    Returns:
        Réponse générée par le LLM
    """
    logger.info(f"Nouvelle requête pour le modèle: {request.model}")
    
    start_time = time.time()
    
    try:
        # Génération de la réponse
        result = await ollama_client.generate(
            prompt=request.prompt,
            model=request.model,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            context=request.context
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Réponse générée en {elapsed_time:.2f}s")
        
        return LLMResponse(**result)
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération: {str(e)}"
        )


@app.post("/generate", response_model=LLMResponse)
async def generate(request: PromptRequest):
    """
    Alias pour /ask (compatibilité)
    """
    return await ask(request)


@app.get("/")
async def root():
    """
    Endpoint racine
    """
    return {
        "service": "Néron LLM Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "models": "/models",
            "ask": "/ask (POST)",
            "generate": "/generate (POST)"
        }
    }


# ----------------------------
# Point d'entrée
# ----------------------------

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.ENV == "development"
    )
