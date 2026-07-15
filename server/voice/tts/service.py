from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from voice.config import load_voice_config
from voice.models import SpeechResult
from voice.tts.pipeline import validate_tts_text
from voice.tts.providers import PiperFfmpegProvider
from voice.tts.providers.base import TtsProvider

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="voice_tts")
_provider: TtsProvider | None = None


def load_engine() -> TtsProvider:
    global _provider
    config = load_voice_config().tts
    if config.provider != "piper":
        raise RuntimeError(f"Provider TTS non supporté : {config.provider}")
    _provider = PiperFfmpegProvider(config)
    return _provider


def check_connection() -> bool:
    return _provider is not None


async def speak(text: str, options: dict[str, Any] | None = None) -> SpeechResult:
    config = load_voice_config().tts
    fmt = str((options or {}).get("format") or config.format)
    normalized = validate_tts_text(text, config.max_chars)
    if _provider is None:
        raise RuntimeError("Moteur TTS non chargé")
    return await asyncio.get_event_loop().run_in_executor(
        _executor,
        _speak_sync,
        normalized,
        fmt,
    )


def _speak_sync(text: str, fmt: str) -> SpeechResult:
    start = time.monotonic()
    assert _provider is not None
    result = _provider.synthesize(text, fmt)
    metadata = dict(result.metadata)
    metadata["chars"] = len(text)
    metadata["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
    return SpeechResult(
        audio=result.audio,
        format=result.format,
        duration=result.duration,
        metadata=metadata,
    )
