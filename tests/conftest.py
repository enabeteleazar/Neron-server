# tests/conftest.py
import sys
import pytest

sys.path.insert(0, "/mnt/usb-storage/Neron_AI/modules/neron_core")


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
