# modules/neron_tts/app.py
# Neron TTS v1.0.0 - Service de synthese vocale

import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from engine import get_engine, TTSEngine

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("neron_tts")

VERSION = "1.0.0"
TTS_MAX_CHARS = int(os.getenv("TTS_MAX_CHARS", "1000"))

_startup_time: float = 0.0
_tts_engine: TTSEngine = None


class Metrics:
    def __init__(self):
        self._syntheses_total: int = 0
        self._errors_total: int = 0
        self._latencies: list = []

    def record_success(self, latency_ms: float):
        self._syntheses_total += 1
        self._latencies.append(latency_ms)
        if len(self._latencies) > 1000:
            self._latencies = self._latencies[-1000:]

    def record_error(self):
        self._syntheses_total += 1
        self._errors_total += 1

    def export(self) -> str:
        lines = []
        uptime = round(time.monotonic() - _startup_time, 2)
        lines += [
            "# HELP neron_tts_uptime_seconds Uptime du service",
            "# TYPE neron_tts_uptime_seconds gauge",
            f"neron_tts_uptime_seconds {uptime}",
            "# HELP neron_tts_syntheses_total Nombre total de syntheses",
            "# TYPE neron_tts_syntheses_total counter",
            f"neron_tts_syntheses_total {self._syntheses_total}",
            "# HELP neron_tts_errors_total Erreurs de synthese",
            "# TYPE neron_tts_errors_total counter",
            f"neron_tts_errors_total {self._errors_total}",
        ]
        if self._latencies:
            avg = round(sum(self._latencies) / len(self._latencies), 2)
            lines += [
                "# HELP neron_tts_latency_avg_ms Latence moyenne (ms)",
                "# TYPE neron_tts_latency_avg_ms gauge",
                f"neron_tts_latency_avg_ms {avg}",
            ]
        return "\n".join(lines) + "\n"


metrics = Metrics()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tts_engine, _startup_time
    _startup_time = time.monotonic()

    engine_name = os.getenv("TTS_ENGINE", "pyttsx3")
    logger.info(f"Chargement moteur TTS '{engine_name}'...")
    _tts_engine = get_engine()

    startup_ms = round((time.monotonic() - _startup_time) * 1000, 0)
    logger.info(f"TTS engine '{_tts_engine.name()}' pret en {startup_ms}ms")
    yield
    logger.info("Arret neron_tts")


app = FastAPI(
    title="Neron TTS",
    description="Service synthese vocale - pyttsx3",
    version=VERSION,
    lifespan=lifespan
)


class SynthesizeRequest(BaseModel):
    text: str
    engine: str = None  # override optionnel


@app.get("/")
def root():
    return {
        "service": "Neron TTS",
        "version": VERSION,
        "engine": _tts_engine.name() if _tts_engine else "loading",
        "max_chars": TTS_MAX_CHARS,
        "endpoints": {
            "synthesize": "POST /synthesize -> audio/wav",
            "health": "GET /health",
            "metrics": "GET /metrics"
        }
    }


@app.get("/health")
def health():
    return {
        "status": "healthy" if _tts_engine is not None else "loading",
        "version": VERSION,
        "engine": _tts_engine.name() if _tts_engine else None
    }


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return PlainTextResponse(metrics.export(), media_type="text/plain")


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    if _tts_engine is None:
        raise HTTPException(503, "Moteur TTS non charge")

    text = request.text.strip()
    if not text:
        raise HTTPException(400, "Texte vide")

    if len(text) > TTS_MAX_CHARS:
        raise HTTPException(
            413,
            f"Texte trop long : {len(text)} chars > {TTS_MAX_CHARS} max"
        )

    logger.info(f"Synthese : {len(text)} chars : '{text[:60]}...'")

    try:
        start = time.monotonic()
        audio_bytes = _tts_engine.synthesize(text)
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        metrics.record_success(latency_ms)
        logger.info(f"Synthese OK : {latency_ms}ms -> {len(audio_bytes)} bytes")

        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "X-TTS-Engine": _tts_engine.name(),
                "X-TTS-Latency-Ms": str(latency_ms),
                "X-TTS-Chars": str(len(text))
            }
        )

    except Exception as e:
        metrics.record_error()
        logger.error(f"Erreur synthese : {e}")
        raise HTTPException(500, f"Erreur de synthese : {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
