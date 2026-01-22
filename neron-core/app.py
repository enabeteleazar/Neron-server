from fastapi import FastAPI, UploadFile, File
import requests

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Néron v0.1 actif"}

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
