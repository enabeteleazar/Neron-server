# modules/neron_stt/app.py
# Neron STT v1.0.0 - Service de transcription audio via Whisper

import logging
import os
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import whisper
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("neron_stt")

VERSION = "1.0.0"
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", None)  # None = detection auto
WHISPER_DOWNLOAD_ROOT = os.getenv("WHISPER_DOWNLOAD_ROOT", "/app/models")
SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}

_startup_time: float = 0.0
_whisper_model = None


class Metrics:
    def __init__(self):
        self._transcriptions_total: int = 0
        self._transcriptions_errors: int = 0
        self._latencies: list = []

    def record_success(self, latency_ms: float):
        self._transcriptions_total += 1
        self._latencies.append(latency_ms)
        if len(self._latencies) > 1000:
            self._latencies = self._latencies[-1000:]

    def record_error(self):
        self._transcriptions_total += 1
        self._transcriptions_errors += 1

    def export(self) -> str:
        lines = []
        uptime = round(time.monotonic() - _startup_time, 2)

        lines += [
            "# HELP neron_stt_uptime_seconds Duree depuis le demarrage",
            "# TYPE neron_stt_uptime_seconds gauge",
            f"neron_stt_uptime_seconds {uptime}",
        ]
        lines += [
            "# HELP neron_stt_transcriptions_total Nombre total de transcriptions",
            "# TYPE neron_stt_transcriptions_total counter",
            f"neron_stt_transcriptions_total {self._transcriptions_total}",
        ]
        lines += [
            "# HELP neron_stt_errors_total Nombre d erreurs de transcription",
            "# TYPE neron_stt_errors_total counter",
            f"neron_stt_errors_total {self._transcriptions_errors}",
        ]
        if self._latencies:
            avg = round(sum(self._latencies) / len(self._latencies), 2)
            lines += [
                "# HELP neron_stt_latency_avg_ms Latence moyenne de transcription (ms)",
                "# TYPE neron_stt_latency_avg_ms gauge",
                f"neron_stt_latency_avg_ms {avg}",
            ]

        return "\n".join(lines) + "\n"


metrics = Metrics()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _whisper_model, _startup_time

    _startup_time = time.monotonic()
    logger.info(f"Chargement du modele Whisper '{WHISPER_MODEL_NAME}'...")
    _whisper_model = whisper.load_model(
        WHISPER_MODEL_NAME,
        download_root=WHISPER_DOWNLOAD_ROOT
    )
    lang_info = WHISPER_LANGUAGE if WHISPER_LANGUAGE else "detection auto"
    logger.info(f"Modele Whisper '{WHISPER_MODEL_NAME}' charge. Langue : {lang_info}")
    yield
    logger.info("Arret neron_stt")


app = FastAPI(
    title="Neron STT",
    description="Service de transcription audio - Whisper",
    version=VERSION,
    lifespan=lifespan
)


class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration_ms: float
    model: str
    timestamp: str


@app.get("/")
def root():
    return {
        "service": "Neron STT",
        "version": VERSION,
        "model": WHISPER_MODEL_NAME,
        "language": WHISPER_LANGUAGE or "auto",
        "supported_formats": list(SUPPORTED_FORMATS),
        "endpoints": {
            "transcribe": "POST /transcribe",
            "health": "GET /health",
            "metrics": "GET /metrics"
        }
    }


@app.get("/health")
def health():
    return {
        "status": "healthy" if _whisper_model is not None else "loading",
        "version": VERSION,
        "model": WHISPER_MODEL_NAME,
        "language": WHISPER_LANGUAGE or "auto"
    }


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return PlainTextResponse(metrics.export(), media_type="text/plain")


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)):
    ext = ""
    if file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower()

    if ext not in SUPPORTED_FORMATS:
        metrics.record_error()
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporte : '{ext}'. Formats acceptes : {SUPPORTED_FORMATS}"
        )

    if _whisper_model is None:
        metrics.record_error()
        raise HTTPException(503, "Modele Whisper non charge")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        logger.info(f"Transcription de '{file.filename}' ({len(content)} bytes)")

        start = time.monotonic()

        # Options de transcription
        transcribe_options = {}
        if WHISPER_LANGUAGE:
            transcribe_options["language"] = WHISPER_LANGUAGE

        result = _whisper_model.transcribe(tmp_path, **transcribe_options)
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        text = result.get("text", "").strip()
        language = result.get("language", "unknown")

        metrics.record_success(latency_ms)
        logger.info(
            f"Transcription OK : {latency_ms}ms | "
            f"langue: {language} | texte: {text[:80]}"
        )

        return TranscribeResponse(
            text=text,
            language=language,
            duration_ms=latency_ms,
            model=WHISPER_MODEL_NAME,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        metrics.record_error()
        logger.error(f"Erreur transcription : {e}")
        raise HTTPException(500, f"Erreur de transcription : {str(e)}")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
