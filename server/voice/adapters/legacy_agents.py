from __future__ import annotations

import time

from agents.builtin.base_agent import AgentResult, get_logger
from voice import stt, tts

logger = get_logger("voice.legacy_agents")


def load_stt_model() -> object:
    return stt.load_model()


def load_tts_engine() -> object:
    return tts.load_engine()


class STTAgent:
    def __init__(self) -> None:
        logger.info("STTAgent init - voice module")

    async def transcribe(self, audio_bytes: bytes, filename: str) -> AgentResult:
        start = time.monotonic()
        try:
            result = await stt.transcribe(audio_bytes, filename)
            latency_ms = result.metadata.get(
                "latency_ms",
                result.metadata.get("duration_ms", round((time.monotonic() - start) * 1000, 2)),
            )
            return AgentResult(
                success=True,
                content=result.text,
                source="stt_agent",
                error=None,
                latency_ms=latency_ms,
                metadata={
                    **result.metadata,
                    "language": result.language,
                    "confidence": result.confidence,
                },
            )
        except Exception as exc:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            logger.error(f"Erreur transcription : {exc}")
            return AgentResult(
                success=False,
                content="",
                source="stt_agent",
                error=f"Erreur transcription : {exc}",
                latency_ms=latency_ms,
                metadata={},
            )

    async def reload(self) -> bool:
        try:
            stt.load_model()
            return True
        except Exception as exc:
            logger.error(f"STT reload error: {exc}")
            return False

    async def check_connection(self) -> bool:
        return stt.check_connection()


class TTSAgent:
    def __init__(self) -> None:
        logger.info("TTSAgent init - voice module")

    async def synthesize(self, text: str) -> AgentResult:
        start = time.monotonic()
        try:
            result = await tts.speak(text)
            latency_ms = result.metadata.get("latency_ms", round((time.monotonic() - start) * 1000, 2))
            return AgentResult(
                success=True,
                content="",
                source="tts_agent",
                error=None,
                latency_ms=latency_ms,
                metadata={
                    **result.metadata,
                    "audio_bytes": result.audio,
                    "format": result.format,
                    "duration": result.duration,
                },
            )
        except Exception as exc:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            logger.error(f"Erreur TTS : {exc}")
            return AgentResult(
                success=False,
                content="",
                source="tts_agent",
                error=f"Erreur synthèse : {exc}",
                latency_ms=latency_ms,
                metadata={},
            )

    async def reload(self) -> bool:
        try:
            tts.load_engine()
            return True
        except Exception as exc:
            logger.error(f"TTS reload error: {exc}")
            return False

    async def check_connection(self) -> bool:
        return tts.check_connection()
