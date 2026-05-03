"""
neron-stt — Service de transcription vocale
FastAPI + faster-whisper, port 8001
"""

import logging
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel

# ── Config ──────────────────────────────────────────────────────────────────

YAML_PATH = Path("/etc/neron/neron.yaml")
LOG_LEVEL  = logging.INFO


def load_config() -> dict:
    try:
        with open(YAML_PATH) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


cfg     = load_config()
stt_cfg = cfg.get("stt", {})

MODEL_SIZE   = stt_cfg.get("model",    "small")
LANGUAGE     = stt_cfg.get("language", "fr")
DEVICE       = stt_cfg.get("device",   "cpu")
COMPUTE_TYPE = stt_cfg.get("compute_type", "int8")
PORT         = int(stt_cfg.get("port", 8001))
API_KEY      = cfg.get("neron", {}).get("api_key", "")

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [neron-stt] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("neron-stt")

# ── Model lifecycle ──────────────────────────────────────────────────────────

model: WhisperModel | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    log.info(f"Chargement modèle Whisper '{MODEL_SIZE}' ({DEVICE}/{COMPUTE_TYPE})...")
    t0 = time.time()
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    log.info(f"Modèle prêt en {time.time() - t0:.1f}s")
    yield
    log.info("Arrêt neron-stt")


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="neron-stt", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth middleware ──────────────────────────────────────────────────────────

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/"):
        return await call_next(request)
    if API_KEY:
        key = request.headers.get("X-API-Key", "")
        if key != API_KEY:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"service": "neron-stt", "status": "ok"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model":  MODEL_SIZE,
        "device": DEVICE,
        "language": LANGUAGE,
        "ready": model is not None,
    }


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(503, "Modèle non chargé")

    # Écrire l'audio dans un fichier temporaire
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        t0 = time.time()
        segments, info = model.transcribe(
            tmp_path,
            language=LANGUAGE,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        elapsed = time.time() - t0

        log.info(f"Transcription ({elapsed:.2f}s, lang={info.language}): {text!r}")

        return {
            "text":     text,
            "language": info.language,
            "duration": round(elapsed, 2),
        }
    finally:
        os.unlink(tmp_path)


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
