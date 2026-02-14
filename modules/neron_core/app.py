from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import httpx
import logging
import os
from typing import Optional

# Configuration du logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Néron Core",
    description="Orchestrateur central de l'assistant Néron",
    version="0.2.0"
)

# Configuration des services
NERON_LLM_URL = os.getenv("NERON_LLM_URL", "http://neron-llm:11434")
NERON_MEMORY_URL = os.getenv("NERON_MEMORY_URL", "http://neron-memory:8002")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

# Timeouts
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60.0"))
MEMORY_TIMEOUT = float(os.getenv("MEMORY_TIMEOUT", "5.0"))


class CoreResponse(BaseModel):
    response: str
    transcription: Optional[str] = None
    metadata: dict = {}


class TextInput(BaseModel):
    text: str


@app.get("/")
def root():
    return {
        "service": "Néron Core",
        "version": "0.2.0",
        "status": "active"
    }


@app.get("/health")
def health():
    """Healthcheck endpoint pour Docker"""
    return {"status": "healthy"}


@app.post("/input/text", response_model=CoreResponse)
async def text_input(input_data: TextInput):
    """
    Pipeline texte : Text → LLM → Memory
    """
    logger.info(f"Receiving text input: {input_data.text[:100]}...")
    
    try:
        async with httpx.AsyncClient() as client:
            
            # === ÉTAPE 1 : Génération LLM ===
            logger.info("Calling LLM service...")
            try:
                llm_response = await client.post(
                    f"{NERON_LLM_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": input_data.text,
                        "stream": False
                    },
                    timeout=LLM_TIMEOUT
                )
                llm_response.raise_for_status()
                llm_data = llm_response.json()
                response_text = llm_data.get("response", "").strip()
                
                if not response_text:
                    response_text = "Je n'ai pas pu générer de réponse."
                
                logger.info(f"LLM response: {response_text[:100]}...")
                
            except httpx.TimeoutException:
                logger.error("LLM service timeout")
                raise HTTPException(504, "Language model service timeout")
            except httpx.HTTPStatusError as e:
                logger.error(f"LLM service error: {e}")
                raise HTTPException(503, f"Language model service error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"LLM unexpected error: {e}")
                raise HTTPException(500, f"Language model processing failed: {str(e)}")

            # === ÉTAPE 2 : Stockage en mémoire ===
            logger.info("Storing in memory...")
            try:
                await client.post(
                    f"{NERON_MEMORY_URL}/store",
                    json={
                        "input": input_data.text,
                        "response": response_text,
                        "metadata": {"source": "text"}
                    },
                    timeout=MEMORY_TIMEOUT
                )
            except Exception as e:
                logger.warning(f"Memory storage error (non-blocking): {e}")

        return CoreResponse(
            response=response_text,
            metadata={"model": OLLAMA_MODEL}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in text pipeline: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
