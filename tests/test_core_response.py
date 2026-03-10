# tests/test_core_response.py
# Tests de la structure de réponse du endpoint /input/text

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import sys

sys.path.insert(0, "/mnt/usb-storage/Neron_AI/modules/neron_core")


def make_intent_result(intent, confidence="high"):
    from orchestrator.intent_router import IntentResult
    r = IntentResult.__new__(IntentResult)
    r.intent = intent
    r.confidence = confidence
    return r


def make_llm_success():
    return MagicMock(
        success=True,
        content="Bonjour ! Comment puis-je vous aider ?",
        latency_ms=1200.0,
        metadata={"model": "llama3.2:3b"}
    )


def make_web_success():
    return MagicMock(
        success=True,
        content="Resultats de recherche",
        latency_ms=500.0,
        metadata={"sources": ["http://example.com"], "total_results": 3}
    )


def make_time_provider():
    """Mock time_provider avec now() retournant un vrai datetime"""
    mock = MagicMock()
    fixed_dt = datetime(2026, 2, 20, 8, 11, 0, tzinfo=timezone.utc)
    mock.now.return_value = fixed_dt
    mock.human.return_value = "vendredi 20 février 2026 à 08h11"
    mock.iso.return_value = "2026-02-20T08:11:00+00:00"
    mock.timestamp.return_value = 1771571460.0
    return mock


@pytest.fixture
def client():
    from orchestrator.intent_router import Intent

    mock_llm = MagicMock()
    mock_llm.execute = AsyncMock(return_value=make_llm_success())

    mock_web = MagicMock()
    mock_web.execute = AsyncMock(return_value=make_web_success())

    mock_router = MagicMock()
    mock_router.route = AsyncMock(
        return_value=make_intent_result(Intent.CONVERSATION)
    )

    mock_tp = make_time_provider()

    with patch("app.LLMAgent", return_value=mock_llm), \
         patch("app.WebAgent", return_value=mock_web), \
         patch("app.IntentRouter", return_value=mock_router), \
         patch("app.TimeProvider", return_value=mock_tp):

        from app import app
        with TestClient(app) as c:
            yield c, mock_router


def _post(c, text):
    return c.post("/input/text", json={"text": text})


# --- Structure de base ---

def test_response_has_all_fields(client):
    c, _ = client
    r = _post(c, "bonjour").json()
    for field in ["response", "intent", "agent", "confidence",
                  "timestamp", "execution_time_ms", "model", "error"]:
        assert field in r, f"Champ manquant : {field}"


def test_timestamp_is_utc_iso(client):
    c, _ = client
    r = _post(c, "bonjour").json()
    parsed = datetime.fromisoformat(r["timestamp"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_execution_time_ms_is_positive(client):
    c, _ = client
    r = _post(c, "bonjour").json()
    assert r["execution_time_ms"] >= 0


def test_error_is_null_on_success(client):
    c, _ = client
    r = _post(c, "bonjour").json()
    assert r["error"] is None


# --- Conversation ---

def test_conversation_agent(client):
    c, _ = client
    r = _post(c, "bonjour").json()
    assert r["agent"] == "llm_agent"
    assert r["intent"] == "conversation"
    assert r["model"] == "llama3.2:3b"


# --- TIME_QUERY ---

def test_time_query_agent(client):
    c, mock_router = client
    from orchestrator.intent_router import Intent
    mock_router.route = AsyncMock(
        return_value=make_intent_result(Intent.TIME_QUERY)
    )
    r = _post(c, "quelle heure est-il").json()
    assert r["agent"] == "time_provider"
    assert r["intent"] == "time_query"
    assert r["model"] is None
    assert r["error"] is None


def test_time_query_execution_time_fast(client):
    c, mock_router = client
    from orchestrator.intent_router import Intent
    mock_router.route = AsyncMock(
        return_value=make_intent_result(Intent.TIME_QUERY)
    )
    r = _post(c, "quelle heure est-il").json()
    assert r["execution_time_ms"] < 100


# --- WEB_SEARCH ---

def test_web_search_agent(client):
    c, mock_router = client
    from orchestrator.intent_router import Intent
    mock_router.route = AsyncMock(
        return_value=make_intent_result(Intent.WEB_SEARCH)
    )
    r = _post(c, "cherche la meteo").json()
    assert r["agent"] == "web_agent+llm_agent"
    assert r["intent"] == "web_search"
