from __future__ import annotations

import asyncio
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

from voice.config import load_voice_config
from voice.models import TranscriptionResult
from voice.stt.pipeline import validate_audio_input
from voice.stt.providers import FasterWhisperProvider
from voice.stt.providers.base import SttProvider

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="voice_stt")
_provider: SttProvider | None = None


def _build_provider() -> SttProvider:
    config = load_voice_config().stt
    if config.provider != "whisper":
        raise RuntimeError(f"Provider STT non supporté : {config.provider}")
    return FasterWhisperProvider(config)


def load_model() -> object:
    global _provider
    _provider = _build_provider()
    return _provider.load()


def check_connection() -> bool:
    return _provider is not None and _provider.is_ready()


async def transcribe(audio: bytes, filename: str = "audio.wav") -> TranscriptionResult:
    config = load_voice_config().stt
    ext = validate_audio_input(audio, filename, config.max_size_mb)
    if _provider is None or not _provider.is_ready():
        raise RuntimeError("Modèle STT non chargé")
    return await asyncio.get_event_loop().run_in_executor(
        _executor,
        _transcribe_sync,
        audio,
        ext,
    )


def _transcribe_sync(audio: bytes, ext: str) -> TranscriptionResult:
    start = time.monotonic()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(audio)
            tmp_path = tmp.name
        assert _provider is not None
        result = _provider.transcribe_file(tmp_path)
        metadata = dict(result.metadata)
        metadata.setdefault("duration_ms", round((time.monotonic() - start) * 1000, 2))
        return TranscriptionResult(
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            metadata=metadata,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
