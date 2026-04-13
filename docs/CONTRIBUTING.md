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

-----

## Code de Conduite

### Notre Engagement

Nous nous engageons à faire de la participation à ce projet une expérience exempte de harcèlement pour tous, indépendamment de l’âge, de la taille corporelle, du handicap visible ou invisible, de l’ethnicité, des caractéristiques sexuelles, de l’identité et de l’expression de genre, du niveau d’expérience, de l’éducation, du statut socio-économique, de la nationalité, de l’apparence personnelle, de la race, de la religion ou de l’identité et de l’orientation sexuelles.

### Nos Standards

**Comportements positifs :**

- Utiliser un langage accueillant et inclusif
- Respecter les différents points de vue et expériences
- Accepter gracieusement les critiques constructives
- Se concentrer sur ce qui est le mieux pour la communauté
- Faire preuve d’empathie envers les autres membres

**Comportements inacceptables :**

- Langage ou images sexualisés, attention sexuelle non sollicitée
- Trolling, commentaires insultants, attaques personnelles ou politiques
- Harcèlement public ou privé
- Publication d’informations privées sans permission explicite
- Toute autre conduite raisonnablement considérée comme inappropriée

-----

## Comment Contribuer

### 🐛 Signaler des Bugs

Avant de créer un rapport de bug, vérifiez la [liste des issues](https://github.com/enabeteleazar/Neron_AI/issues) pour voir si le problème a déjà été signalé.

1. Utilisez le template d’issue “Bug Report”
1. Fournissez un titre clair et descriptif
1. Décrivez les étapes exactes pour reproduire le problème
1. Fournissez des exemples si possible
1. Décrivez le comportement attendu vs observé
1. Incluez les logs pertinents
1. Spécifiez votre environnement (OS, Python, version Néron AI)

### 💡 Suggérer des Fonctionnalités

1. Utilisez le template d’issue “Feature Request”
1. Fournissez un titre clair et descriptif
1. Décrivez la fonctionnalité en détail
1. Expliquez pourquoi elle serait utile
1. Proposez une implémentation si possible

### 🔧 Contribuer du Code

1. **Fork** le projet
1. **Clone** votre fork
1. **Créer** une branche feature
1. **Développer** et **tester**
1. **Commit** vos changements
1. **Push** vers votre fork
1. **Ouvrir** une Pull Request

-----

## Configuration de l’Environnement

### Prérequis

- Python 3.11+
- Git
- Ollama installé localement
- Un éditeur de code (VS Code recommandé)

> ⚠️ Néron AI v2.0 est **natif, sans Docker**. Aucun Docker requis pour contribuer.

### Installation pour le Développement

```bash
# 1. Forker et cloner le dépôt
git clone https://github.com/VOTRE_USERNAME/Neron_AI.git
cd Neron_AI

# 2. Copier et configurer les variables d'environnement
cp .env.example .env
# Éditer .env selon votre configuration locale

# 3. Installer les dépendances Python
make install

# 4. Télécharger un modèle Ollama
make ollama

# 5. Lancer Néron en mode développement
make start
```

### Configuration de l’Éditeur

**VS Code (recommandé) :**

Extensions recommandées : Python, Pylance, Black Formatter, autoDocstring

Configuration `.vscode/settings.json` :

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true
}
```

-----

## Workflow de Développement

### 1. Créer une Branche

```bash
# Nouvelle fonctionnalité
git checkout -b feature/nom-de-la-fonctionnalite

# Bugfix
git checkout -b fix/description-du-bug

# Documentation
git checkout -b docs/description
```

### 2. Développer

- Écrivez du code clair et documenté
- Suivez les [Standards de Code](#standards-de-code)
- Ajoutez des tests pour vos modifications
- Mettez à jour la documentation si nécessaire

### 3. Tester

```bash
# Tous les tests
make test

# Tests d'un module spécifique
cd neron_core
pytest -v

# Avec coverage
pytest --cov=. --cov-report=html

# Linter
flake8 .

# Formatter
black .
```

### 4. Commit

Utilisez la convention [Conventional Commits](https://www.conventionalcommits.org/) :

```
<type>(<scope>): <description>

[corps optionnel]

[footer optionnel]
```

**Types :**

- `feat` : Nouvelle fonctionnalité
- `fix` : Correction de bug
- `docs` : Documentation seulement
- `style` : Formatage, cosmétique
- `refactor` : Refactoring sans nouvelle feature ni bugfix
- `test` : Ajout ou correction de tests
- `chore` : Maintenance, configuration

**Exemples :**

```bash
git commit -m "feat(llm): ajoute support du streaming"
git commit -m "fix(core): corrige timeout sur requêtes longues"
git commit -m "docs(readme): met à jour guide d'installation"
git commit -m "test(memory): ajoute tests pour la recherche"
```

### 5. Push et Pull Request

```bash
git push origin feature/nom-de-la-fonctionnalite
# Puis ouvrir une Pull Request sur GitHub
```

-----

## Standards de Code

### Python

**Style :**

- Suivez [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Formatage via [Black](https://black.readthedocs.io/) (88 chars/ligne)
- Linting via [flake8](https://flake8.pycqa.org/)

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
    return result
```

**Docstrings :**

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Description courte de la fonction.

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

### Structure de Projet

```
neron_core/
├── app.py               # Application principale (point d'entrée unique)
├── config.py            # Configuration
├── models.py            # Modèles Pydantic
├── agents/              # Agents intégrés
│   ├── llm_agent.py
│   ├── stt_agent.py
│   ├── tts_agent.py
│   ├── memory_agent.py
│   ├── telegram_agent.py
│   └── watchdog_agent.py
├── requirements.txt     # Dépendances
└── tests/               # Tests
    ├── __init__.py
    ├── conftest.py
    └── test_*.py
```

-----

## Tests

### Philosophie

- Tous les nouveaux codes doivent être testés
- Coverage minimum : **80%**, cible : **90%+**
- Tests unitaires rapides (< 1s chacun)
- Tests d’intégration pour les workflows complets

### Écrire des Tests

```python
import pytest

def test_feature_name():
    """Description claire de ce qui est testé"""
    # Arrange
    input_data = "test"

    # Act
    result = my_function(input_data)

    # Assert
    assert result == expected_output
```

**Tests asynchrones :**

```python
@pytest.mark.asyncio
async def test_async_feature():
    result = await async_function()
    assert result is not None
```

**Mocking :**

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_with_mock():
    with patch('module.external_call', AsyncMock(return_value="mocked")):
        result = await my_function()
        assert result == "mocked"
```

### Lancer les Tests

```bash
# Via Makefile
make test

# Directement
pytest -v
pytest --cov=. --cov-report=html
pytest tests/test_app.py::test_health_check

# Mode watch
ptw
```

-----

## Documentation

### Quoi Documenter

- **README.md** : Vue d’ensemble, installation, usage
- **API** : Tous les endpoints avec exemples de requête/réponse
- **Configuration** : Variables d’environnement et valeurs par défaut
- **Architecture** : Décisions de design importantes

### Format de Documentation

```markdown
# Module Name

Description courte.

## Usage

\`\`\`python
example code
\`\`\`

## API

### POST /endpoint

Description.

**Request:**
\`\`\`json
{"key": "value"}
\`\`\`

**Response:**
\`\`\`json
{"result": "..."}
\`\`\`

## Configuration

| Variable | Description | Défaut |
|----------|-------------|--------|
| VAR_NAME | Description | value  |
```

-----

## Pull Requests

### Checklist

- [ ] Code suit les standards du projet
- [ ] Tous les tests passent (`make test`)
- [ ] Coverage ≥ 80%
- [ ] Documentation mise à jour
- [ ] CHANGELOG.md mis à jour
- [ ] Commits suivent le format conventionnel
- [ ] Pas de conflits avec `master`
- [ ] Description de la PR claire et complète

### Description de PR

```markdown
## Description
Décrivez vos changements en détail.

## Type de Changement
- [ ] 🐛 Bug fix
- [ ] ✨ New feature
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

## Related Issues
Closes #123
```

### Process de Review

1. **CI** — tests et linting automatiques
1. **Code review** — au moins un mainteneur
1. **Discussion** — répondez aux commentaires
1. **Approbation** — au moins une approbation requise
1. **Merge** — squash and merge par défaut

-----

## Reporting de Bugs

### Template

```markdown
## Description
Description claire et concise du bug.

## Reproduction
1. ...
2. ...
3. See error

## Comportement Attendu
Ce qui devrait se passer.

## Comportement Observé
Ce qui se passe réellement.

## Environnement
- OS: [e.g. Ubuntu 22.04]
- Python version: [e.g. 3.11.5]
- Version Néron AI: [e.g. 2.0.0]
- Ollama version: [e.g. 0.6.0]

## Logs
\`\`\`
coller les logs ici
\`\`\`

## Contexte Additionnel
Tout autre contexte utile.
```

-----

## Suggestions de Fonctionnalités

### Template

```markdown
## Problème à Résoudre
Description du problème que cette feature résoudrait.

## Solution Proposée
Description claire de ce que vous souhaitez.

## Alternatives Considérées
Autres solutions envisagées.

## Implémentation Suggérée (optionnel)
Si vous avez une idée d'implémentation.
```

-----

## Questions

- **Issues GitHub** : bugs et features → [github.com/enabeteleazar/Neron_AI/issues](https://github.com/enabeteleazar/Neron_AI/issues)
- **Discussions GitHub** : questions générales

**Comment poser une bonne question :**

1. Recherchez d’abord dans les issues existantes
1. Soyez clair et concis
1. Fournissez du contexte et des logs
1. Décrivez ce que vous avez déjà essayé

-----

## Reconnaissance des Contributeurs

Tous les contributeurs seront listés dans AUTHORS.md et les release notes.

-----

## Ressources

- [Python PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [Black](https://black.readthedocs.io/)
- [Pytest](https://docs.pytest.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Ollama](https://ollama.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)

-----

**Merci pour votre contribution à Néron AI ! 🎉**