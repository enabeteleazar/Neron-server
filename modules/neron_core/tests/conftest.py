# modules/neron_core/tests/conftest.py
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

ROOT = Path(__file__).parent.parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def mock_llm_success():
    agent = MagicMock()
    result = MagicMock()
    result.success = True
    result.content = "CONVERSATION"
    result.metadata = {}
    result.latency_ms = 123.4
    agent.execute = AsyncMock(return_value=result)
    return agent


@pytest.fixture
def mock_llm_failure():
    agent = MagicMock()
    result = MagicMock()
    result.success = False
    result.content = ""
    result.error = "LLM timeout"
    result.latency_ms = 60000.0
    agent.execute = AsyncMock(return_value=result)
    return agent


@pytest.fixture
def mock_searxng_response():
    return {
        "results": [
            {
                "title": "Python - Wikipedia",
                "url": "https://fr.wikipedia.org/wiki/Python",
                "content": "Python est un langage de programmation."
            },
            {
                "title": "Python.org",
                "url": "https://www.python.org",
                "content": "Site officiel de Python."
            }
        ]
    }
