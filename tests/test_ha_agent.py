# tests/test_ha_agent.py
# Tests unitaires pour HAAgent

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import sys
sys.path.insert(0, "/mnt/usb-storage/Neron_AI/modules/neron_core")

from agents.ha_agent import HAAgent, _parse_query, _build_response, _normalize


# --- Tests parsing ---

def test_normalize():
    assert _normalize("Allumé") == "allume"
    assert _normalize("Éteins") == "eteins"

def test_parse_turn_on():
    r = _parse_query("allume la lumiere du salon")
    assert r["action"] == "turn_on"
    assert r["domain"] == "light"
    assert r["room"] == "salon"
    assert r["entity_id"] == "light.salon"

def test_parse_turn_off():
    r = _parse_query("eteins la lumiere du salon")
    assert r["action"] == "turn_off"
    assert r["domain"] == "light"

def test_parse_volet():
    r = _parse_query("ferme le volet du garage")
    assert r["action"] == "turn_off"
    assert r["domain"] == "cover"
    assert r["room"] == "garage"

def test_parse_thermostat():
    r = _parse_query("active le thermostat")
    assert r["domain"] == "climate"

def test_parse_no_room():
    r = _parse_query("allume la lumiere")
    assert r["room"] is None
    assert r["entity_id"] == "light.lumiere"

def test_build_response_on():
    r = _build_response({"action": "turn_on", "domain": "light",
                         "domain_label": "lumiere", "room_label": "salon"})
    assert "allum" in r.lower()
    assert "salon" in r.lower()

def test_build_response_off():
    r = _build_response({"action": "turn_off", "domain": "light",
                         "domain_label": "lumiere", "room_label": None})
    assert "teint" in r.lower()

def test_build_response_cover():
    r = _build_response({"action": "turn_off", "domain": "cover",
                         "domain_label": "volet", "room_label": "garage"})
    assert "ferm" in r.lower()


# --- Tests agent ---

@pytest.fixture
def agent():
    return HAAgent()


@pytest.mark.asyncio
async def test_ha_disabled(agent):
    """HA désactivé retourne erreur"""
    with patch("agents.ha_agent.HA_ENABLED", False):
        result = await agent.execute("allume la lumiere")
    assert result.success is False
    assert "non activ" in result.error.lower()


@pytest.mark.asyncio
async def test_ha_no_token(agent):
    """Token manquant retourne erreur"""
    with patch("agents.ha_agent.HA_ENABLED", True), \
         patch("agents.ha_agent.HA_TOKEN", ""):
        result = await agent.execute("allume la lumiere")
    assert result.success is False
    assert "token" in result.error.lower()


@pytest.mark.asyncio
async def test_ha_execute_success(agent):
    """Exécution réussie retourne AgentResult success"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("agents.ha_agent.HA_ENABLED", True), \
         patch("agents.ha_agent.HA_TOKEN", "fake_token"), \
         patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await agent.execute("allume la lumiere du salon")

    assert result.success is True
    assert result.source == "ha_agent"
    assert result.metadata["entity_id"] == "light.salon"
    assert result.metadata["action"] == "turn_on"


@pytest.mark.asyncio
async def test_ha_timeout(agent):
    with patch("agents.ha_agent.HA_ENABLED", True), \
         patch("agents.ha_agent.HA_TOKEN", "fake_token"), \
         patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await agent.execute("allume la lumiere")

    assert result.success is False
    assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_ha_token_invalide(agent):
    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("agents.ha_agent.HA_ENABLED", True), \
         patch("agents.ha_agent.HA_TOKEN", "bad_token"), \
         patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await agent.execute("allume la lumiere")

    assert result.success is False
    assert "token" in result.error.lower()


@pytest.mark.asyncio
async def test_check_connection_disabled(agent):
    with patch("agents.ha_agent.HA_ENABLED", False):
        result = await agent.check_connection()
    assert result is False


@pytest.mark.asyncio
async def test_check_connection_ok(agent):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("agents.ha_agent.HA_ENABLED", True), \
         patch("agents.ha_agent.HA_TOKEN", "fake_token"), \
         patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await agent.check_connection()

    assert result is True
