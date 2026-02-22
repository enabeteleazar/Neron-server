# agents/stt_agent.py
# Neron Core - Agent STT (client HTTP vers neron_stt)

import os
import time
from pathlib import Path

import httpx

from agents.base_agent import AgentResult, get_logger

logger = get_logger("stt_agent")

STT_URL = os.getenv("NERON_STT_URL", "http://neron_stt:8001")
STT_TIMEOUT = float(os.getenv("STT_TIMEOUT", "60.0"))
SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}


class STTAgent:
    def __init__(self):
        self.url = STT_URL
        self.timeout = STT_TIMEOUT
        logger.info(f"STTAgent init : {self.url}")

    async def transcribe(self, audio_bytes: bytes, filename: str) -> AgentResult:
        ext = Path(filename).suffix.lower()

        if ext not in SUPPORTED_FORMATS:
            return AgentResult(
                success=False,
                content="",
                source="stt_agent",
                error=f"Format non supporte : '{ext}'",
                latency_ms=0.0,
                metadata={}
            )

        start = time.monotonic()
        logger.info(f"Transcription : '{filename}' ({len(audio_bytes)} bytes)")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.url}/transcribe",
                    files={"file": (filename, audio_bytes, "audio/wav")}
                )
                response.raise_for_status()
                data = response.json()

            latency_ms = round((time.monotonic() - start) * 1000, 2)
            text = data.get("text", "").strip()
            language = data.get("language", "unknown")
            model = data.get("model", "unknown")

            logger.info(f"Transcription OK : {latency_ms}ms | langue: {language} | texte: {text[:80]}")

            return AgentResult(
                success=True,
                content=text,
                source="stt_agent",
                error=None,
                latency_ms=latency_ms,
                metadata={
                    "language": language,
                    "stt_model": model,
                    "filename": filename,
                    "duration_ms": data.get("duration_ms", 0)
                }
            )

        except httpx.TimeoutException:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            error = f"stt timeout apres {self.timeout}s"
            logger.error(f"[stt_agent] {error}")
            return AgentResult(
                success=False,
                content="",
                source="stt_agent",
                error=error,
                latency_ms=latency_ms,
                metadata={}
            )

        except httpx.HTTPStatusError as e:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            error = f"stt erreur HTTP {e.response.status_code}"
            logger.error(f"[stt_agent] {error}")
            return AgentResult(
                success=False,
                content="",
                source="stt_agent",
                error=error,
                latency_ms=latency_ms,
                metadata={}
            )

        except Exception as e:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            error = f"stt inaccessible : {str(e)}"
            logger.error(f"[stt_agent] {error}")
            return AgentResult(
                success=False,
                content="",
                source="stt_agent",
                error=error,
                latency_ms=latency_ms,
                metadata={}
            )

    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.url}/health")
                return r.status_code == 200
        except Exception:
            return False
