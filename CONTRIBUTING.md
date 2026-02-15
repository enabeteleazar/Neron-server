# Guide de Contribution

Merci de votre intérêt pour contribuer à Néron AI ! 🎉

Ce document fournit des guidelines pour contribuer au projet. En participant, vous acceptez de respecter notre [Code de Conduite](#code-de-conduite).

## 📋 Table des Matières

- [Code de Conduite](#code-de-conduite)
- [Comment Contribuer](#comment-contribuer)
- [Configuration de l’Environnement](#configuration-de-lenvironnement)
- [Workflow de Développement](#workflow-de-développement)
- [Standards de Code](#standards-de-code)
- [Tests](#tests)
- [Documentation](#documentation)
- [Pull Requests](#pull-requests)
- [Reporting de Bugs](#reporting-de-bugs)
- [Suggestions de Fonctionnalités](#suggestions-de-fonctionnalités)
- [Questions](#questions)

## Code de Conduite

### Notre Engagement

Nous nous engageons à faire de la participation à ce projet une expérience exempte de harcèlement pour tous, indépendamment de l’âge, de la taille corporelle, du handicap visible ou invisible, de l’ethnicité, des caractéristiques sexuelles, de l’identité et de l’expression de genre, du niveau d’expérience, de l’éducation, du statut socio-économique, de la nationalité, de l’apparence personnelle, de la race, de la religion ou de l’identité et de l’orientation sexuelles.

### Nos Standards

**Exemples de comportements qui contribuent à créer un environnement positif :**

- Utiliser un langage accueillant et inclusif
- Respecter les différents points de vue et expériences
- Accepter gracieusement les critiques constructives
- Se concentrer sur ce qui est le mieux pour la communauté
- Faire preuve d’empathie envers les autres membres

**Exemples de comportements inacceptables :**

- Langage ou images sexualisés, attention sexuelle non sollicitée
- Trolling, commentaires insultants ou dérogatoires, attaques personnelles ou politiques
- Harcèlement public ou privé
- Publication d’informations privées sans permission explicite
- Autre conduite raisonnablement considérée comme inappropriée

## Comment Contribuer

Il existe plusieurs façons de contribuer à Néron AI :

### 🐛 Signaler des Bugs

Avant de créer un rapport de bug, vérifiez la [liste des issues](https://github.com/yourusername/neron-ai/issues) pour voir si le problème a déjà été signalé.

**Comment signaler un bug :**

1. Utilisez le template d’issue “Bug Report”
1. Fournissez un titre clair et descriptif
1. Décrivez les étapes exactes pour reproduire le problème
1. Fournissez des exemples de code si possible
1. Décrivez le comportement attendu vs observé
1. Incluez les logs et captures d’écran pertinents
1. Spécifiez votre environnement (OS, version Docker, etc.)

### 💡 Suggérer des Fonctionnalités

**Comment suggérer une fonctionnalité :**

1. Utilisez le template d’issue “Feature Request”
1. Fournissez un titre clair et descriptif
1. Décrivez la fonctionnalité en détail
1. Expliquez pourquoi cette fonctionnalité serait utile
1. Proposez une implémentation si possible

### 🔧 Contribuer du Code

1. **Fork** le projet
1. **Clone** votre fork
1. **Créer** une branche feature
1. **Développer** et **tester**
1. **Commit** vos changements
1. **Push** vers votre fork
1. **Ouvrir** une Pull Request

## Configuration de l’Environnement

### Prérequis

- Python 3.11+
- Docker 20.10+
- Docker Compose 2.0+
- Git
- Un éditeur de code (VS Code recommandé)

### Installation pour le Développement

```bash
# 1. Forker et cloner le dépôt
git clone https://github.com/VOTRE_USERNAME/neron-ai.git
cd neron-ai

# 2. Créer le réseau Docker
docker network create Neron_Network

# 3. Copier et configurer les variables d'environnement
cp .env.example /opt/Homebox_AI/.env

# 4. Installer les dépendances Python pour le développement
pip install -r requirements-dev.txt

# 5. Installer les pre-commit hooks
pre-commit install

# 6. Lancer les services en mode développement
docker compose up -d

# 7. Télécharger un modèle de test
docker exec -it neron_ollama ollama pull llama3.2:1b
```

### Configuration de l’Éditeur

**VS Code (recommandé) :**

Installer les extensions suivantes :

- Python
- Docker
- Pylance
- Black Formatter
- autoDocstring

Configuration `.vscode/settings.json` :

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

## Workflow de Développement

### 1. Créer une Branche

```bash
# Pour une nouvelle fonctionnalité
git checkout -b feature/nom-de-la-fonctionnalite

# Pour un bugfix
git checkout -b fix/description-du-bug

# Pour de la documentation
git checkout -b docs/description
```

### 2. Développer

- Écrivez du code clair et documenté
- Suivez les [Standards de Code](#standards-de-code)
- Ajoutez des tests pour vos modifications
- Mettez à jour la documentation si nécessaire

### 3. Tester

```bash
# Tests unitaires d'un module spécifique
cd modules/neron_llm
pytest -v

# Tests avec coverage
pytest --cov=. --cov-report=html

# Linter
flake8 .

# Formatter
black .

# Type checking
mypy .
```

### 4. Commit

Utilisez des messages de commit clairs et descriptifs suivant la convention [Conventional Commits](https://www.conventionalcommits.org/) :

```bash
# Format
<type>(<scope>): <description>

[corps optionnel]

[footer optionnel]
```

**Types :**

- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation seulement
- `style`: Formatage, points-virgules manquants, etc.
- `refactor`: Refactoring de code
- `test`: Ajout de tests
- `chore`: Maintenance, configuration

**Exemples :**

```bash
git commit -m "feat(llm): ajoute support du streaming"
git commit -m "fix(core): corrige timeout sur requêtes longues"
git commit -m "docs(readme): met à jour guide d'installation"
git commit -m "test(memory): ajoute tests pour la recherche"
```

### 5. Push et Pull Request

```bash
# Push vers votre fork
git push origin feature/nom-de-la-fonctionnalite

# Créer une Pull Request sur GitHub
```

## Standards de Code

### Python

**Style :**

- Suivez [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Utilisez [Black](https://black.readthedocs.io/) pour le formatage
- Utilisez [flake8](https://flake8.pycqa.org/) pour le linting
- Maximum 88 caractères par ligne (Black default)

**Type Hints :**

```python
def process_text(text: str, max_length: int = 100) -> Dict[str, Any]:
    """
    Traite le texte d'entrée.
    
    Args:
        text: Texte à traiter
        max_length: Longueur maximale
        
    Returns:
        Résultat du traitement
    """
    result: Dict[str, Any] = {}
    # ... code ...
    return result
```

**Docstrings :**

- Utilisez le format Google ou NumPy
- Documentez tous les modules, classes et fonctions publiques

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Description courte de la fonction.
    
    Description plus longue si nécessaire.
    
    Args:
        param1: Description du premier paramètre
        param2: Description du second paramètre
        
    Returns:
        Description de la valeur de retour
        
    Raises:
        ValueError: Quand param2 est négatif
        
    Example:
        >>> function_name("test", 5)
        True
    """
    pass
```

**Imports :**

```python
# Standard library
import os
import sys
from typing import Dict, List, Optional

# Third-party
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

# Local
from .config import settings
from .models import Request
```

### Docker

**Dockerfile :**

- Utilisez des images officielles de base
- Multi-stage builds quand approprié
- Minimisez les layers
- Utilisez `.dockerignore`
- Documentez les variables d’environnement

**Docker Compose :**

- Utilisez des noms de services explicites
- Configurez les health checks
- Documentez les volumes et networks
- Utilisez des variables d’environnement

### Structure de Projet

```
module_name/
├── __init__.py          # Exports du module
├── app.py               # Application principale
├── config.py            # Configuration
├── models.py            # Modèles Pydantic
├── client.py            # Client externe (si applicable)
├── requirements.txt     # Dépendances
├── Dockerfile           # Image Docker
├── README.md            # Documentation du module
├── tests/               # Tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_app.py
│   └── test_models.py
└── docs/                # Documentation détaillée
    └── README.md
```

## Tests

### Philosophie

- Tous les nouveaux codes doivent être testés
- Objectif de coverage : **80% minimum, 90%+ idéal**
- Tests unitaires rapides (< 1s chacun)
- Tests d’intégration pour les workflows complets

### Écrire des Tests

**Structure d’un test :**

```python
import pytest

def test_feature_name():
    """Description claire de ce qui est testé"""
    # Arrange - Préparer les données
    input_data = "test"
    
    # Act - Exécuter la fonction
    result = my_function(input_data)
    
    # Assert - Vérifier le résultat
    assert result == expected_output
```

**Tests asynchrones :**

```python
import pytest

@pytest.mark.asyncio
async def test_async_feature():
    """Test d'une fonction async"""
    result = await async_function()
    assert result is not None
```

**Mocking :**

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_with_mock():
    """Test avec mock d'un service externe"""
    with patch('module.external_call', AsyncMock(return_value="mocked")):
        result = await my_function()
        assert result == "mocked"
```

### Lancer les Tests

```bash
# Tests d'un module
cd modules/neron_llm
pytest -v

# Avec coverage
pytest --cov=. --cov-report=html

# Tests spécifiques
pytest tests/test_app.py::test_health_check

# Mode watch (install pytest-watch)
ptw
```

### Coverage

```bash
# Générer un rapport de coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Voir le rapport
open htmlcov/index.html
```

## Documentation

### Quoi Documenter

- **README.md** : Vue d’ensemble du module
- **API** : Tous les endpoints avec exemples
- **Configuration** : Variables d’environnement
- **Exemples** : Cas d’utilisation courants
- **Architecture** : Décisions de design importantes

### Format de Documentation

**Module README :**

```markdown
# Module Name

Description courte

## Features
- Feature 1
- Feature 2

## Usage
```python
example code
```

## API

### Endpoint Name

Description

**Request:**

```json
example
```

**Response:**

```json
example
```

## Configuration

Variables d’environnement…

```
## Pull Requests

### Checklist

Avant de soumettre une PR, assurez-vous que :

- [ ] Le code suit les standards du projet
- [ ] Tous les tests passent
- [ ] Coverage ≥ 80%
- [ ] Documentation mise à jour
- [ ] CHANGELOG.md mis à jour
- [ ] Commits suivent le format conventionnel
- [ ] Pas de conflits avec main
- [ ] PR description claire et complète

### Description de PR

Utilisez le template suivant :

```markdown
## Description
Décrivez vos changements en détail.

## Type de Changement
- [ ] 🐛 Bug fix (non-breaking change)
- [ ] ✨ New feature (non-breaking change)
- [ ] 💥 Breaking change
- [ ] 📝 Documentation
- [ ] 🔧 Refactoring

## Comment Tester
Décrivez comment tester vos changements.

## Checklist
- [ ] Tests ajoutés/mis à jour
- [ ] Documentation mise à jour
- [ ] CHANGELOG mis à jour
- [ ] Code formatté (black)
- [ ] Linter passé (flake8)

## Screenshots (si applicable)

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks** : CI/CD vérifie les tests et le linting
1. **Code review** : Au moins un mainteneur review le code
1. **Discussion** : Répondez aux commentaires et questions
1. **Approbation** : Au moins une approbation requise
1. **Merge** : Squash and merge par défaut

## Reporting de Bugs

### Template d’Issue Bug

```markdown
## Description
Description claire et concise du bug.

## Reproduction
Étapes pour reproduire :
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

## Comportement Attendu
Ce qui devrait se passer.

## Comportement Observé
Ce qui se passe réellement.

## Screenshots
Si applicable, ajoutez des screenshots.

## Environnement
- OS: [e.g. Ubuntu 22.04]
- Docker version: [e.g. 24.0.0]
- Python version: [e.g. 3.11.5]
- Version Néron AI: [e.g. 1.0.0]

## Logs
```

Coller les logs pertinents

```
## Contexte Additionnel
Tout autre contexte utile.
```

## Suggestions de Fonctionnalités

### Template d’Issue Feature

```markdown
## Problème à Résoudre
Description du problème que cette feature résoudrait.

## Solution Proposée
Description claire de ce que vous voulez.

## Alternatives Considérées
Autres solutions que vous avez envisagées.

## Contexte Additionnel
Screenshots, mockups, exemples de code.

## Implémentation Suggérée (optionnel)
Si vous avez une idée d'implémentation.
```

## Questions

### Où Poser des Questions

- **Issues GitHub** : Pour les bugs et features
- **Discussions GitHub** : Pour les questions générales
- **Email** : support@neron-ai.example.com

### Comment Poser une Bonne Question

1. Recherchez d’abord dans les issues existantes
1. Soyez clair et concis
1. Fournissez du contexte
1. Incluez des exemples de code si pertinent
1. Décrivez ce que vous avez déjà essayé

## Reconnaissance des Contributeurs

Tous les contributeurs seront listés dans :

- Le fichier AUTHORS.md
- La section “Contributors” sur GitHub
- Les release notes

## Ressources

### Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Documentation](docs/API.md)
- [FAQ](docs/FAQ.md)

### Outils

- [Python PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [Black](https://black.readthedocs.io/)
- [Pytest](https://docs.pytest.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Docker](https://docs.docker.com/)

### Communauté

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [License](LICENSE)

-----

**Merci pour votre contribution à Néron AI ! 🎉**

Votre aide est précieuse pour améliorer le projet.
