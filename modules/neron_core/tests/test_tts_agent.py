# tests/test_tts_agent.py
# Tests unitaires pour TTSAgent

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.tts_agent import TTSAgent


@pytest.fixture
def agent():
    return TTSAgent()


@pytest.fixture
def mock_audio_bytes():
    return b"RIFF" + b"\x00" * 100  # fake WAV


# --- Tests texte vide ---

@pytest.mark.asyncio
async def test_texte_vide_rejete(agent):
    """Texte vide retourne erreur"""
    result = await agent.synthesize("")
    assert result.success is False
    assert "vide" in result.error.lower()
    assert result.source == "tts_agent"


@pytest.mark.asyncio
async def test_texte_espaces_rejete(agent):
    """Texte avec espaces seulement retourne erreur"""
    result = await agent.synthesize("   ")
    assert result.success is False
    assert result.source == "tts_agent"


# --- Tests synthese ---

@pytest.mark.asyncio
async def test_synthese_succes(agent, mock_audio_bytes):
    """Synthese reussie retourne AgentResult success"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = mock_audio_bytes
    mock_response.headers = {"X-TTS-Engine": "pyttsx3"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.synthesize("Bonjour Neron")

    assert result.success is True
    assert result.source == "tts_agent"
    assert result.error is None
    assert result.metadata["audio_bytes"] == mock_audio_bytes
    assert result.metadata["engine"] == "pyttsx3"
    assert result.metadata["chars"] == len("Bonjour Neron")


@pytest.mark.asyncio
async def test_synthese_latency_presente(agent, mock_audio_bytes):
    """Latence presente dans le resultat"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = mock_audio_bytes
    mock_response.headers = {"X-TTS-Engine": "pyttsx3"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.synthesize("Test latence")

    assert result.latency_ms is not None
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_synthese_timeout(agent):
    """Timeout retourne AgentResult echec"""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.synthesize("Test timeout")

    assert result.success is False
    assert "timeout" in result.error.lower()
    assert result.source == "tts_agent"


@pytest.mark.asyncio
async def test_synthese_http_error(agent):
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

        result = await agent.synthesize("Test HTTP error")

    assert result.success is False
    assert "500" in result.error
    assert result.source == "tts_agent"


@pytest.mark.asyncio
async def test_synthese_service_indisponible(agent):
    """Service inaccessible retourne AgentResult echec"""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await agent.synthesize("Test service down")

    assert result.success is False
    assert result.source == "tts_agent"


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
