from __future__ import annotations

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

from voice.models import SpeechResult, TranscriptionResult
from voice.normalization import normalize_french_text
from voice.stt.pipeline import validate_audio_input
from voice.tts.pipeline import validate_tts_text


def test_normalize_french_text_basic_cleanup() -> None:
    assert normalize_french_text("  bonjour  néron  ! ") == "Bonjour Néron!"
    assert normalize_french_text("ok neron") == "OK Néron"


def test_validate_audio_input_rejects_unknown_format() -> None:
    with pytest.raises(ValueError, match="Format non supporté"):
        validate_audio_input(b"abc", "clip.txt", 10)


def test_validate_tts_text_limits_empty_and_long_text() -> None:
    assert validate_tts_text(" bonjour ", 20) == "bonjour"
    with pytest.raises(ValueError, match="Texte vide"):
        validate_tts_text(" ", 20)
    with pytest.raises(ValueError, match="Texte trop long"):
        validate_tts_text("bonjour", 3)


@pytest.mark.asyncio
async def test_legacy_stt_adapter_keeps_agent_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from voice.adapters.legacy_agents import STTAgent
    from voice import stt

    async def fake_transcribe(audio: bytes, filename: str) -> TranscriptionResult:
        assert audio == b"audio"
        assert filename == "clip.wav"
        return TranscriptionResult(text="Bonjour", language="fr", metadata={"stt_model": "fake"})

    monkeypatch.setattr(stt, "transcribe", fake_transcribe)
    result = await STTAgent().transcribe(b"audio", "clip.wav")
    assert result.success is True
    assert result.content == "Bonjour"
    assert result.metadata["language"] == "fr"


@pytest.mark.asyncio
async def test_legacy_tts_adapter_keeps_agent_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from voice.adapters.legacy_agents import TTSAgent
    from voice import tts

    async def fake_speak(text: str) -> SpeechResult:
        assert text == "Bonjour"
        return SpeechResult(
            audio=b"audio",
            format="mp3",
            duration=None,
            metadata={"mimetype": "audio/mpeg", "engine": "fake"},
        )

    monkeypatch.setattr(tts, "speak", fake_speak)
    result = await TTSAgent().synthesize("Bonjour")
    assert result.success is True
    assert result.metadata["audio_bytes"] == b"audio"
    assert result.metadata["mimetype"] == "audio/mpeg"
