# tests/test_tts_agent.py
# Tests unitaires pour TTSAgent (pyttsx3 direct, pas HTTP)

import pytest
from unittest.mock import MagicMock, patch
import sys


from agents.tts_agent import TTSAgent


@pytest.fixture
def agent():
    return TTSAgent()


@pytest.fixture
def mock_tts_engine():
    """Mock du moteur TTS"""
    engine = MagicMock()
    engine.name.return_value = "pyttsx3"
    engine.synthesize.return_value = b"RIFF" + b"\x00" * 100
    return engine


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


# --- Moteur non chargé ---

@pytest.mark.asyncio
async def test_moteur_non_charge(agent):
    """Retourne erreur si moteur non chargé"""
    with patch("agents.tts_agent._tts_engine", None):
        result = await agent.synthesize("Bonjour")
    assert result.success is False
    assert "non chargé" in result.error.lower()


# --- Tests synthèse ---

@pytest.mark.asyncio
async def test_synthese_succes(agent, mock_tts_engine):
    """Synthèse réussie retourne AgentResult success"""
    with patch("agents.tts_agent._tts_engine", mock_tts_engine):
        result = await agent.synthesize("Bonjour Neron")

    assert result.success is True
    assert result.source == "tts_agent"
    assert result.error is None
    assert result.metadata["engine"] == "pyttsx3"
    assert result.metadata["chars"] == len("Bonjour Neron")
    assert len(result.metadata["audio_bytes"]) > 0


@pytest.mark.asyncio
async def test_synthese_latency_presente(agent, mock_tts_engine):
    """Latence présente dans le résultat"""
    with patch("agents.tts_agent._tts_engine", mock_tts_engine):
        result = await agent.synthesize("Test latence")

    assert result.latency_ms is not None
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_synthese_erreur_engine(agent):
    """Exception engine retourne AgentResult échec"""
    engine = MagicMock()
    engine.synthesize.side_effect = RuntimeError("engine crash")

    with patch("agents.tts_agent._tts_engine", engine):
        result = await agent.synthesize("Test erreur")

    assert result.success is False
    assert "engine crash" in result.error.lower()
    assert result.source == "tts_agent"


# --- check_connection ---

@pytest.mark.asyncio
async def test_check_connection_ok(agent, mock_tts_engine):
    """Moteur chargé → True"""
    with patch("agents.tts_agent._tts_engine", mock_tts_engine):
        result = await agent.check_connection()
    assert result is True


@pytest.mark.asyncio
async def test_check_connection_echec(agent):
    """Moteur non chargé → False"""
    with patch("agents.tts_agent._tts_engine", None):
        result = await agent.check_connection()
    assert result is False
