# tests/conftest.py
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Chemin relatif depuis ce fichier → modules/neron_core
ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "modules" / "neron_core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

print(f"[conftest] ROOT ajoute au path : {CORE}")

@pytest.fixture
def mock_searxng_response():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "results": [
            {"title": "Test", "url": "https://example.com", "content": "Contenu test"}
        ]
    }
    return mock
