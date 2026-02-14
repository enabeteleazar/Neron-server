# Tests - Néron LLM

## 📋 Structure des tests

```
tests/
├── __init__.py              # Package de tests
├── conftest.py              # Fixtures pytest partagées
├── pytest.ini               # Configuration pytest
├── test_app.py              # Tests de l'application FastAPI
├── test_ollama_client.py    # Tests du client Ollama
├── test_models.py           # Tests des modèles Pydantic
└── README.md                # Ce fichier
```

## 🧪 Lancer les tests

### Tests unitaires (rapides, avec mocks)

```bash
# Tous les tests
pytest

# Avec verbosité
pytest -v

# Avec coverage
pytest --cov=. --cov-report=html

# Tests spécifiques
pytest tests/test_app.py
pytest tests/test_ollama_client.py
pytest tests/test_models.py

# Un test particulier
pytest tests/test_app.py::test_root_endpoint
```

### Tests d'intégration (nécessitent Ollama)

```bash
# Marquer comme tests d'intégration
pytest -m integration

# Exclure les tests d'intégration
pytest -m "not integration"
```

## 📊 Coverage

```bash
# Générer un rapport de coverage HTML
pytest --cov=. --cov-report=html

# Ouvrir le rapport
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 🎯 Objectifs de coverage

- **Minimum** : 80%
- **Cible** : 90%+
- **Fichiers critiques** : 95%+
  - `app.py`
  - `ollama_client.py`
  - `models.py`

## 🔧 Fixtures disponibles

### Depuis `conftest.py`

- `mock_ollama_response` : Réponse Ollama standard
- `mock_ollama_models` : Liste des modèles Ollama
- `mock_httpx_client` : Client HTTP mocké

### Depuis `test_app.py`

- `mock_ollama_client_instance` : Instance OllamaClient mockée
- `client` : Client TestClient FastAPI

## 📝 Écrire de nouveaux tests

### Template pour un test unitaire

```python
import pytest

def test_my_feature():
    """Description du test"""
    # Arrange
    input_data = "test"
    
    # Act
    result = my_function(input_data)
    
    # Assert
    assert result == expected_output
```

### Template pour un test async

```python
import pytest

@pytest.mark.asyncio
async def test_my_async_feature():
    """Description du test"""
    result = await my_async_function()
    assert result is not None
```

### Template pour un test avec mock

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_with_mock():
    """Description du test"""
    with patch('module.function', AsyncMock(return_value="mocked")):
        result = await my_function()
        assert result == "mocked"
```

## 🐛 Debugging

### Afficher les prints

```bash
pytest -s
```

### Arrêter au premier échec

```bash
pytest -x
```

### Mode verbose avec traceback complet

```bash
pytest -vv --tb=long
```

### Lancer un test spécifique en debug

```bash
pytest tests/test_app.py::test_root_endpoint -vv --tb=long -s
```

## 🔍 Vérifications avant commit

```bash
# 1. Formater le code
black .

# 2. Linter
flake8 .

# 3. Type checking
mypy .

# 4. Tests
pytest

# 5. Coverage
pytest --cov=. --cov-report=term-missing
```

## 📚 Ressources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

## ✅ Checklist tests

Avant de merger :

- [ ] Tous les tests passent
- [ ] Coverage > 80%
- [ ] Pas de warnings pytest
- [ ] Tests documentés
- [ ] Fixtures réutilisables
- [ ] Pas de code dupliqué dans les tests
