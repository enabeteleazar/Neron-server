from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from typing import Dict

# Import du modele et de l'orchestrator
from neron.models.message import NeronMessage
from neron.neron_core.orchestrator import Orchestrator
from neron.neron_core.state import NERON_VERSION
from neron.neron_core.state import NERON_NAME   

# Initialise de l'orchestrator
orchestrator = Orchestrator()

# Modèle pour recevoir message JSON
class MessageRequest(BaseModel):
    message: str

# Creation de l'application FastAPI
app = FastAPI(
    title="Néron-Core API",
    description="Coeur de l'AI Néron",
    version="1.0.0"
)

# CORS pour autoriser tous les appels externes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# ENDPOINTS SYSTEME
# ======================

@app.get("/")
def read_root():
    return {
        "service": NERON_NAME,
        "status": "online",
        "version": NERON_VERSION
    }

@app.get("/health")
def health_check():
    """Health check pour Docker"""
    return {"status": "healthy"}

@app.get("/status")
def status() -> Dict[str, str]:
    """Vérifie l'état de tous les services de la stack"""
    return {
        "neron-core": "OK"
    }

# ======================
# ENDPOINT METIER
# ======================

@app.post("/chat")
async def chat(request: MessageRequest):
    """Endpoint pour envoyer un message à Ollama via l'orchestrateur"""
    try:
        incoming_message = NeronMessage(
            source="api",
            target="core",
            content=request.message
        )
        response = orchestrator.handle(incoming_message)
        return {
            "response": response.content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================
# LANCEMENT
# ======================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("NERON_CORE_PORT", 4000))
    uvicorn.run(app, host="0.0.0.0", port=port)