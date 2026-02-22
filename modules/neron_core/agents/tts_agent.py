# agents/tts_agent.py
# Neron Core - Agent TTS (client HTTP vers neron_tts)

import os
import time

import httpx

from agents.base_agent import AgentResult, get_logger

logger = get_logger("tts_agent")

TTS_URL = os.getenv("NERON_TTS_URL", "http://neron_tts:8003")
TTS_TIMEOUT = float(os.getenv("TTS_TIMEOUT", "30.0"))


class TTSAgent:
    def __init__(self):
        self.url = TTS_URL
        self.timeout = TTS_TIMEOUT
        logger.info(f"TTSAgent init : {self.url}")

    async def synthesize(self, text: str) -> AgentResult:
        if not text or not text.strip():
            return AgentResult(
                success=False,
                content="",
                source="tts_agent",
                error="Texte vide",
                latency_ms=0.0,
                metadata={}
            )

        start = time.monotonic()
        logger.info(f"Synthese TTS : '{text[:60]}...' ({len(text)} chars)")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.url}/synthesize",
                    json={"text": text}
                )
                response.raise_for_status()
                audio_bytes = response.content

            latency_ms = round((time.monotonic() - start) * 1000, 2)
            engine = response.headers.get("X-TTS-Engine", "unknown")

            logger.info(f"TTS OK : {latency_ms}ms -> {len(audio_bytes)} bytes")

            return AgentResult(
                success=True,
                content="",
                source="tts_agent",
                error=None,
                latency_ms=latency_ms,
                metadata={
                    "audio_bytes": audio_bytes,
                    "engine": engine,
                    "chars": len(text)
                }
            )

        except httpx.TimeoutException:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            error = f"tts timeout apres {self.timeout}s"
            logger.error(f"[tts_agent] {error}")
            return AgentResult(
                success=False,
                content="",
                source="tts_agent",
                error=error,
                latency_ms=latency_ms,
                metadata={}
            )

        except httpx.HTTPStatusError as e:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            error = f"tts erreur HTTP {e.response.status_code}"
            logger.error(f"[tts_agent] {error}")
            return AgentResult(
                success=False,
                content="",
                source="tts_agent",
                error=error,
                latency_ms=latency_ms,
                metadata={}
            )

        except Exception as e:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            error = f"tts inaccessible : {str(e)}"
            logger.error(f"[tts_agent] {error}")
            return AgentResult(
                success=False,
                content="",
                source="tts_agent",
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
