from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import requests

app = FastAPI()

class TextInput(BaseModel):
    text: str

@app.get("/")
def root():
    return {"message": "Néron v0.1 actif"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/input/text")
async def input_text(data: TextInput):
    # 1️⃣ Envoyer le texte au LLM
    try:
        llm_resp = requests.post(
            LLM_URL,
            json={"prompt": data.text, "model": "llama3.2:1b"}
        ).json()
        llm_text = llm_resp.get("text", "LLM n'a pas répondu")
    except Exception as e:
        llm_text = f"Erreur LLM : {e}"

    # 2️⃣ Stocker dans Memory
    try:
        requests.post(
            MEMORY_URL,
            json={"input": data.text, "response": llm_text}
        )
    except Exception as e:
        print(f"Erreur stockage mémoire : {e}")

    # 3️⃣ Retourner la réponse
    return {"status": "ok", "received": data.text, "llm_response": llm_text}

@app.post("/input/audio")
async def audio_input(file: UploadFile = File(...)):
    # Transcription STT
    stt_resp = requests.post(
        "http://neron-stt:8001/transcribe",
        files={"file": file.file}
    ).json()

    text = stt_resp.get("text", "")

    # Passage LLM
    llm_resp = requests.post(
        "http://neron-llm:11434/api/generate",
        json={"prompt": text, "max_tokens": 100}
    ).json()

    response_text = llm_resp.get("response", "")

    # Mémoire
    requests.post(
        "http://neron-memory:8002/store",
        json={"input": text, "response": response_text}
    )

    return {"response": response_text}
