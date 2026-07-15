# server/voice/app.py
# NéronOS - Microservice Voice (STT/TTS), extrait du process principal neronOS.service

from __future__ import annotations

import base64
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from voice.adapters.legacy_agents import (
    STTAgent,
    TTSAgent,
    load_stt_model,
    load_tts_engine,
)
from voice import stt, tts

logger = logging.getLogger("voice.app")

VERSION = "0.1.0"

stt_agent: STTAgent | None = None
tts_agent: TTSAgent | None = None

_startup_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global stt_agent, tts_agent, _startup_time
    _startup_time = time.monotonic()

    logger.info("Démarrage voice daemon — chargement STT/TTS...")

    stt_agent = STTAgent()
    try:
        load_stt_model()
    except Exception as e:
        logger.error(f"Échec chargement modèle STT au démarrage : {e}")
        # On ne bloque pas le démarrage : /health signalera le provider comme dégradé
        # plutôt que de faire crash-looper tout le service voice.

    tts_agent = TTSAgent()
    try:
        load_tts_engine()
    except Exception as e:
        logger.error(f"Échec chargement moteur TTS au démarrage : {e}")

    logger.info("Voice daemon prêt.")
    yield
    logger.info("Arrêt voice daemon.")


app = FastAPI(title="NéronOS Voice Daemon", version=VERSION, lifespan=lifespan)


class TranscribeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    audio_b64: str = Field(..., description="Audio encodé en base64")
    filename:  str = Field(..., description="Nom de fichier (extension utilisée pour le format)")

    @field_validator("audio_b64")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("audio_b64 ne peut pas être vide")
        return v


class TranscribeResponse(BaseModel):
    success:       bool
    text:          str | None = None
    language:      str | None = None
    latency_ms:    float
    error:         str | None = None
    metadata:      dict[str, Any] = Field(default_factory=dict)


class SynthesizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str = Field(..., min_length=1)


@app.get("/health")
async def health() -> dict:
    return {
        "status":  "ok",
        "version": VERSION,
        "uptime_s": round(time.monotonic() - _startup_time, 2),
        "stt_ready": stt.check_connection(),
        "tts_ready": tts.check_connection(),
    }


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(req: TranscribeRequest) -> TranscribeResponse:
    if stt_agent is None:
        raise HTTPException(status_code=503, detail="STT non disponible")

    try:
        audio_bytes = base64.b64decode(req.audio_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"audio_b64 invalide : {e}")

    result = await stt_agent.transcribe(audio_bytes, req.filename)

    return TranscribeResponse(
        success=result.success,
        text=result.content if result.success else None,
        language=result.metadata.get("language") if result.success else None,
        latency_ms=result.latency_ms,
        error=result.error,
        metadata=result.metadata,
    )


@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest) -> Response:
    if tts_agent is None:
        raise HTTPException(status_code=503, detail="TTS non disponible")

    result = await tts_agent.synthesize(req.text)

    if not result.success:
        raise HTTPException(status_code=422, detail=result.error or "Erreur synthèse TTS")

    audio_bytes = result.metadata.get("audio_bytes", b"")
    mimetype = result.metadata.get("mimetype", "audio/mpeg")

    return Response(content=audio_bytes, media_type=mimetype)


@app.post("/reload")
async def reload_engines() -> dict:
    stt_ok = await stt_agent.reload() if stt_agent else False
    tts_ok = await tts_agent.reload() if tts_agent else False
    return {"stt_reloaded": stt_ok, "tts_reloaded": tts_ok}
