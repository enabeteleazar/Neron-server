# modules/neron_stt/app.py
# Neron STT v1.1.0 - faster-whisper (int8, CPU-optimise)

import logging
import os
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from faster_whisper import WhisperModel
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("neron_stt")

VERSION = "1.1.0"
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", None)
WHISPER_DOWNLOAD_ROOT = os.getenv("WHISPER_DOWNLOAD_ROOT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "models"))
AUDIO_MAX_SIZE_MB = float(os.getenv("AUDIO_MAX_SIZE_MB", "10"))
AUDIO_MAX_SIZE_BYTES = int(AUDIO_MAX_SIZE_MB * 1024 * 1024)
SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}

_startup_time: float = 0.0
_whisper_model: WhisperModel = None


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
            "# HELP neron_stt_transcriptions_total Nombre total de transcriptions",
            "# TYPE neron_stt_transcriptions_total counter",
            f"neron_stt_transcriptions_total {self._transcriptions_total}",
            "# HELP neron_stt_errors_total Erreurs de transcription",
            "# TYPE neron_stt_errors_total counter",
            f"neron_stt_errors_total {self._transcriptions_errors}",
        ]
        if self._latencies:
            avg = round(sum(self._latencies) / len(self._latencies), 2)
            lines += [
                "# HELP neron_stt_latency_avg_ms Latence moyenne (ms)",
                "# TYPE neron_stt_latency_avg_ms gauge",
                f"neron_stt_latency_avg_ms {avg}",
            ]
        return "\n".join(lines) + "\n"


metrics = Metrics()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _whisper_model, _startup_time
    _startup_time = time.monotonic()

    logger.info(f"Chargement faster-whisper '{WHISPER_MODEL_NAME}' (int8, cpu)...")
    _whisper_model = WhisperModel(
        WHISPER_MODEL_NAME,
        device="cpu",
        compute_type="int8",
        download_root=WHISPER_DOWNLOAD_ROOT
    )

    # Warmup : transcription courte pour precharger en memoire
    logger.info("Warmup faster-whisper...")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        import wave, struct
        tmp_path = tmp.name
        with wave.open(tmp_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(struct.pack('<' + 'h' * 1600, *([0] * 1600)))
    try:
        list(_whisper_model.transcribe(tmp_path, language="fr"))
    except Exception:
        pass
    finally:
        os.remove(tmp_path)

    lang_info = WHISPER_LANGUAGE if WHISPER_LANGUAGE else "auto"
    startup_ms = round((time.monotonic() - _startup_time) * 1000, 0)
    logger.info(f"faster-whisper pret en {startup_ms}ms | langue: {lang_info}")
    yield
    logger.info("Arret neron_stt")


app = FastAPI(
    title="Neron STT",
    description="Service transcription audio - faster-whisper int8",
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
        "backend": "faster-whisper",
        "compute_type": "int8",
        "model": WHISPER_MODEL_NAME,
        "language": WHISPER_LANGUAGE or "auto",
        "max_size_mb": AUDIO_MAX_SIZE_MB,
        "supported_formats": list(SUPPORTED_FORMATS),
    }


@app.get("/health")
def health():
    return {
        "status": "healthy" if _whisper_model is not None else "loading",
        "version": VERSION,
        "model": WHISPER_MODEL_NAME,
        "backend": "faster-whisper",
        "language": WHISPER_LANGUAGE or "auto"
    }


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return PlainTextResponse(metrics.export(), media_type="text/plain")


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)):
    # Validation format
    ext = ""
    if file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_FORMATS:
        metrics.record_error()
        raise HTTPException(400, f"Format non supporte : '{ext}'")

    if _whisper_model is None:
        metrics.record_error()
        raise HTTPException(503, "Modele non charge")

    # Lecture et validation taille
    content = await file.read()
    if len(content) > AUDIO_MAX_SIZE_BYTES:
        metrics.record_error()
        raise HTTPException(
            413,
            f"Fichier trop volumineux : {len(content)//1024//1024}MB > {AUDIO_MAX_SIZE_MB}MB max"
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        logger.info(f"Transcription de '{file.filename}' ({len(content)} bytes)")

        start = time.monotonic()

        # Options faster-whisper
        transcribe_kwargs = {"beam_size": 5}
        if WHISPER_LANGUAGE:
            transcribe_kwargs["language"] = WHISPER_LANGUAGE

        segments, info = _whisper_model.transcribe(tmp_path, **transcribe_kwargs)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        language = info.language

        latency_ms = round((time.monotonic() - start) * 1000, 2)
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
