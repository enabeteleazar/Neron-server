# tests/test_stt_agent.py
# Tests unitaires pour STTAgent (faster-whisper direct, pas HTTP)

import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, "/mnt/usb-storage/Neron_AI/modules/neron_core")

from agents.stt_agent import STTAgent


@pytest.fixture
def agent():
    return STTAgent()


@pytest.fixture
def mock_whisper_model():
    """Mock du modèle faster-whisper"""
    mock_seg = MagicMock()
    mock_seg.text = "Bonjour Neron quelle heure est il"

    mock_info = MagicMock()
    mock_info.language = "fr"

    model = MagicMock()
    model.transcribe.return_value = ([mock_seg], mock_info)
    return model


# --- Tests format ---

@pytest.mark.asyncio
async def test_format_wav_accepte(agent, mock_whisper_model):
    """Format .wav accepté"""
    with patch("agents.stt_agent._whisper_model", mock_whisper_model):
        result = await agent.transcribe(b"fake_audio", "test.wav")
    assert result.success is True


@pytest.mark.asyncio
async def test_format_mp3_accepte(agent, mock_whisper_model):
    """Format .mp3 accepté"""
    with patch("agents.stt_agent._whisper_model", mock_whisper_model):
        result = await agent.transcribe(b"fake_audio", "test.mp3")
    assert result.success is True


@pytest.mark.asyncio
async def test_format_invalide_rejete(agent):
    """Format non supporté retourne erreur"""
    result = await agent.transcribe(b"fake_audio", "test.txt")
    assert result.success is False
    assert "non support" in result.error.lower()


@pytest.mark.asyncio
async def test_format_pdf_rejete(agent):
    """Format .pdf rejeté"""
    result = await agent.transcribe(b"fake_audio", "test.pdf")
    assert result.success is False


# --- Modèle non chargé ---

@pytest.mark.asyncio
async def test_modele_non_charge(agent):
    """Retourne erreur si modèle non chargé"""
    with patch("agents.stt_agent._whisper_model", None):
        result = await agent.transcribe(b"fake_audio", "test.wav")
    assert result.success is False
    assert "non chargé" in result.error.lower()


# --- Tests transcription ---

@pytest.mark.asyncio
async def test_transcription_succes(agent, mock_whisper_model):
    """Transcription réussie retourne AgentResult success"""
    with patch("agents.stt_agent._whisper_model", mock_whisper_model):
        result = await agent.transcribe(b"fake_audio", "test.wav")

    assert result.success is True
    assert result.content == "Bonjour Neron quelle heure est il"
    assert result.source == "stt_agent"
    assert result.error is None


@pytest.mark.asyncio
async def test_transcription_metadata(agent, mock_whisper_model):
    """Metadata STT correctement remplie"""
    with patch("agents.stt_agent._whisper_model", mock_whisper_model):
        result = await agent.transcribe(b"fake_audio", "test.wav")

    assert result.metadata["language"] == "fr"
    assert "stt_model" in result.metadata
    assert result.metadata["filename"] == "test.wav"
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_transcription_erreur_whisper(agent):
    """Exception whisper retourne AgentResult échec"""
    model = MagicMock()
    model.transcribe.side_effect = RuntimeError("whisper crash")

    with patch("agents.stt_agent._whisper_model", model):
        result = await agent.transcribe(b"fake_audio", "test.wav")

    assert result.success is False
    assert "whisper crash" in result.error.lower()
    assert result.source == "stt_agent"


# --- Fichier trop volumineux ---

@pytest.mark.asyncio
async def test_fichier_trop_volumineux(agent, mock_whisper_model):
    """Fichier > limite retourne erreur"""
    big_audio = b"x" * (100 * 1024 * 1024)  # 100 MB
    with patch("agents.stt_agent._whisper_model", mock_whisper_model):
        result = await agent.transcribe(big_audio, "test.wav")
    assert result.success is False
    assert "volumineux" in result.error.lower()


# --- check_connection ---

@pytest.mark.asyncio
async def test_check_connection_ok(agent, mock_whisper_model):
    """Modèle chargé → True"""
    with patch("agents.stt_agent._whisper_model", mock_whisper_model):
        result = await agent.check_connection()
    assert result is True


@pytest.mark.asyncio
async def test_check_connection_echec(agent):
    """Modèle non chargé → False"""
    with patch("agents.stt_agent._whisper_model", None):
        result = await agent.check_connection()
    assert result is False
