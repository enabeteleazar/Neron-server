from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import httpx
import logging
import os
from typing import Optional
from tools.search import web_search, format_search_results

# Configuration du logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Néron Core",
    description="Orchestrateur central de l'assistant Néron",
    version="0.2.1"
)

# Configuration des services
NERON_LLM_URL = os.getenv("NERON_LLM_URL", "http://neron-llm:11434")
NERON_MEMORY_URL = os.getenv("NERON_MEMORY_URL", "http://neron-memory:8002")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

# Timeouts
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60.0"))
MEMORY_TIMEOUT = float(os.getenv("MEMORY_TIMEOUT", "5.0"))

# Contexte
CONTEXT_LIMIT = int(os.getenv("CONTEXT_LIMIT", "5"))


class CoreResponse(BaseModel):
    response: str
    transcription: Optional[str] = None
    metadata: dict = {}


class TextInput(BaseModel):
    text: str


async def get_conversation_context(client: httpx.AsyncClient, limit: int = 5) -> str:
    """
    Récupère les derniers échanges pour donner du contexte au LLM
    
    Args:
        client: Client HTTP async
        limit: Nombre d'échanges à récupérer
        
    Returns:
        Contexte formaté pour le LLM
    """
    try:
        response = await client.get(
            f"{NERON_MEMORY_URL}/retrieve",
            params={"limit": limit},
            timeout=MEMORY_TIMEOUT
        )
        response.raise_for_status()
        memories = response.json()
        
        if not memories:
            return ""
        
        # Format optimisé pour neron-custom
        context = "Contexte de notre conversation précédente :\n\n"
        
        for mem in reversed(memories):  # Du plus ancien au plus récent
            # Nettoyer les préfixes [SEARCH]
            user_input = mem['input'].replace('[SEARCH] ', '').strip()
            assistant_response = mem['response'][:150].strip()  # Limiter pour éviter overflow
            
            context += f"User: {user_input}\n"
            context += f"Néron: {assistant_response}\n\n"
        
        context += "---\nRéponds maintenant à la nouvelle question en tenant compte de ce contexte.\n\n"
        
        logger.info(f"Retrieved {len(memories)} messages from memory")
        return context
        
    except Exception as e:
        logger.warning(f"Failed to retrieve context: {e}")
        return ""


@app.get("/")
def root():
    return {
        "service": "Néron Core",
        "version": "0.2.1",
        "status": "active"
    }


@app.get("/health")
def health():
    """Healthcheck endpoint pour Docker"""
    return {"status": "healthy"}


@app.post("/input/text", response_model=CoreResponse)
async def text_input(input_data: TextInput):
    """
    Pipeline texte : Context + Text → LLM → Memory
    """
    logger.info(f"Receiving text input: {input_data.text[:100]}...")
    
    try:
        async with httpx.AsyncClient() as client:
            
            # === ÉTAPE 1 : Récupérer le contexte ===
            logger.info("Retrieving conversation context...")
            context = await get_conversation_context(client, limit=CONTEXT_LIMIT)
            
            # === ÉTAPE 2 : Construire le prompt avec contexte ===
            if context:
                full_prompt = f"{context}User: {input_data.text}\nNéron:"
            else:
                full_prompt = input_data.text
            
            # === ÉTAPE 3 : Génération LLM ===
            logger.info("Calling LLM service...")
            try:
                llm_response = await client.post(
                    f"{NERON_LLM_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": full_prompt,
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

            # === ÉTAPE 4 : Stockage en mémoire ===
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
            metadata={
                "model": OLLAMA_MODEL,
                "context_messages": CONTEXT_LIMIT if context else 0
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in text pipeline: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.post("/search", response_model=CoreResponse)
async def search_and_answer(input_data: TextInput):
    """
    Pipeline recherche : Query → SearXNG → LLM synthesis → Memory
    """
    logger.info(f"Search request: {input_data.text}")
    
    try:
        async with httpx.AsyncClient() as client:
            
            # === ÉTAPE 1 : Recherche web ===
            logger.info("Searching web...")
            search_results = await web_search(input_data.text, num_results=5)
            
            if not search_results:
                return CoreResponse(
                    response="Je n'ai pas pu trouver de résultats pour ta recherche.",
                    metadata={
                        "search_query": input_data.text,
                        "results_count": 0
                    }
                )
            
            # === ÉTAPE 2 : Formater pour le LLM ===
            context = format_search_results(search_results)
            
            # === ÉTAPE 3 : Synthèse par le LLM ===
            prompt = f"""Voici des résultats de recherche web pour la question : "{input_data.text}"

{context}

Synthétise ces informations de manière claire et concise en français. Cite les sources pertinentes."""

            logger.info("Calling LLM for synthesis...")
            try:
                llm_response = await client.post(
                    f"{NERON_LLM_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=LLM_TIMEOUT
                )
                llm_response.raise_for_status()
                llm_data = llm_response.json()
                response_text = llm_data.get("response", "").strip()
                
                if not response_text:
                    response_text = context
                
                logger.info(f"Synthesis complete: {response_text[:100]}...")
                
            except Exception as e:
                logger.error(f"LLM synthesis failed: {e}")
                response_text = context
            
            # === ÉTAPE 4 : Stockage en mémoire ===
            logger.info("Storing in memory...")
            try:
                await client.post(
                    f"{NERON_MEMORY_URL}/store",
                    json={
                        "input": f"[SEARCH] {input_data.text}",
                        "response": response_text,
                        "metadata": {
                            "source": "web_search",
                            "results_count": len(search_results)
                        }
                    },
                    timeout=MEMORY_TIMEOUT
                )
            except Exception as e:
                logger.warning(f"Memory storage failed: {e}")
            
            return CoreResponse(
                response=response_text,
                metadata={
                    "model": OLLAMA_MODEL,
                    "search_query": input_data.text,
                    "results_count": len(search_results),
                    "sources": [r["url"] for r in search_results[:3]]
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search pipeline error: {e}")
        raise HTTPException(500, f"Internal error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
