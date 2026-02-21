# tests/test_stt_agent.py
# Tests unitaires pour STTAgent

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.stt_agent import STTAgent


@pytest.fixture
def agent():
    return STTAgent()


@pytest.fixture
def mock_stt_response():
    return {
        "text": "Bonjour Neron quelle heure est il",
        "language": "fr",
        "duration_ms": 7863.0,
        "model": "base",
        "timestamp": "2026-02-21T20:00:00+00:00"
    }


# --- Tests format ---

@pytest.mark.asyncio
async def test_format_wav_accepte(agent):
    """Format .wav accepte"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "text": "test", "language": "fr",
        "duration_ms": 100.0, "model": "base", "timestamp": "2026-01-01T00:00:00+00:00"
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.transcribe(b"fake_audio", "test.wav")

    assert result.success is True


@pytest.mark.asyncio
async def test_format_mp3_accepte(agent):
    """Format .mp3 accepte"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "text": "test", "language": "fr",
        "duration_ms": 100.0, "model": "base", "timestamp": "2026-01-01T00:00:00+00:00"
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.transcribe(b"fake_audio", "test.mp3")

    assert result.success is True


@pytest.mark.asyncio
async def test_format_invalide_rejete(agent):
    """Format non supporte retourne erreur"""
    result = await agent.transcribe(b"fake_audio", "test.txt")
    assert result.success is False
    assert "Format non supporte" in result.error


@pytest.mark.asyncio
async def test_format_pdf_rejete(agent):
    """Format .pdf rejete"""
    result = await agent.transcribe(b"fake_audio", "test.pdf")
    assert result.success is False


# --- Tests transcription ---

@pytest.mark.asyncio
async def test_transcription_succes(agent, mock_stt_response):
    """Transcription reussie retourne AgentResult success"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_stt_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.transcribe(b"fake_audio", "test.wav")

    assert result.success is True
    assert result.content == "Bonjour Neron quelle heure est il"
    assert result.source == "stt_agent"
    assert result.error is None


@pytest.mark.asyncio
async def test_transcription_metadata(agent, mock_stt_response):
    """Metadata STT correctement remplie"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_stt_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.transcribe(b"fake_audio", "test.wav")

    assert result.metadata["language"] == "fr"
    assert result.metadata["stt_model"] == "base"
    assert result.metadata["filename"] == "test.wav"
    assert result.latency_ms is not None
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_transcription_timeout(agent):
    """Timeout retourne AgentResult echec"""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.transcribe(b"fake_audio", "test.wav")

    assert result.success is False
    assert "timeout" in result.error.lower()
    assert result.source == "stt_agent"


@pytest.mark.asyncio
async def test_transcription_http_error(agent):
    """Erreur HTTP retourne AgentResult echec"""
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=mock_response)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.transcribe(b"fake_audio", "test.wav")

    assert result.success is False
    assert "500" in result.error
    assert result.source == "stt_agent"


@pytest.mark.asyncio
async def test_transcription_service_indisponible(agent):
    """Service inaccessible retourne AgentResult echec"""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.transcribe(b"fake_audio", "test.wav")

    assert result.success is False
    assert result.source == "stt_agent"


# --- Tests check_connection ---

@pytest.mark.asyncio
async def test_check_connection_ok(agent):
    """Health check OK retourne True"""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.check_connection()

    assert result is True


@pytest.mark.asyncio
async def test_check_connection_echec(agent):
    """Service down retourne False"""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.check_connection()

    assert result is False
