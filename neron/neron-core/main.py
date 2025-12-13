from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import httpx
from typing import Dict

app = FastAPI(
    title="Néron-Core API",
    description="API centrale de l'assistant Néron",
    version="1.0.0"
)

# CORS pour les appels depuis d'autres services
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration des endpoints des services
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
N8N_URL = os.getenv("N8N_URL", "http://n8n:5678")
NODE_RED_URL = os.getenv("NODE_RED_URL", "http://node-red:1880")

@app.get("/")
def read_root():
    return {
        "service": "neron-core",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    """Health check pour Docker"""
    return {"status": "healthy"}

@app.get("/status")
async def status() -> Dict[str, str]:
    """Vérifie l'état de tous les services de la stack"""
    services_status = {
        "neron-core": "OK"
    }
    
    # Vérifier Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            services_status["ollama"] = "OK" if response.status_code == 200 else "ERROR"
    except Exception as e:
        services_status["ollama"] = f"OFFLINE: {str(e)}"
    
    # Vérifier n8n
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{N8N_URL}/healthz")
            services_status["n8n"] = "OK" if response.status_code == 200 else "ERROR"
    except Exception:
        services_status["n8n"] = "OFFLINE"
    
    # Vérifier Node-RED
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{NODE_RED_URL}/")
            services_status["node-red"] = "OK" if response.status_code == 200 else "ERROR"
    except Exception:
        services_status["node-red"] = "OFFLINE"
    
    return services_status

@app.post("/chat")
async def chat(message: str):
    """Endpoint pour envoyer un message à Ollama"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": os.getenv("OLLAMA_MODEL", "llama2"),
                    "prompt": message,
                    "stream": False
                }
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Ollama: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("NERON_CORE_PORT", 4000))
    uvicorn.run(app, host="0.0.0.0", port=port)
