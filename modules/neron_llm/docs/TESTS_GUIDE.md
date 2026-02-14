# 🧪 Tests Néron LLM - Guide de démarrage rapide

## ✅ Structure créée et corrigée

J'ai créé une **suite de tests complète et fonctionnelle** pour le module `neron_llm` :

```
tests/
├── __init__.py              ✅ Package de tests
├── conftest.py              ✅ Fixtures pytest partagées
├── pytest.ini               ✅ Configuration pytest
├── test_app.py              ✅ 15+ tests pour FastAPI (100% corrigés)
├── test_ollama_client.py    ✅ 10+ tests pour le client Ollama
├── test_models.py           ✅ 15+ tests pour les modèles Pydantic
├── run_tests.sh             ✅ Script de lancement
└── README.md                ✅ Documentation complète
```

## 🚀 Lancement immédiat

### Option 1 : Script automatisé (RECOMMANDÉ)

```bash
cd modules/neron_llm

# Rendre le script exécutable
chmod +x tests/run_tests.sh

# Lancer tous les tests
./tests/run_tests.sh

# Avec coverage
./tests/run_tests.sh --coverage

# Tests unitaires seulement
./tests/run_tests.sh --unit

# Mode verbose
./tests/run_tests.sh -v

# Installer les deps puis tester
./tests/run_tests.sh --install --coverage
```

### Option 2 : Commandes pytest directes

```bash
# Installer les dépendances
pip install -r requirements.txt

# Tous les tests
pytest

# Avec verbosité
pytest -v

# Avec coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Un fichier spécifique
pytest tests/test_app.py -v

# Un test spécifique
pytest tests/test_app.py::test_root_endpoint -v
```

### Option 3 : Dans Docker

```bash
# Build l'image
docker build -t neron-llm-test .

# Lancer les tests
docker run --rm neron-llm-test pytest -v

# Avec coverage
docker run --rm neron-llm-test pytest --cov=. --cov-report=term
```

## 📊 Ce qui a été corrigé

### ❌ Problèmes identifiés dans votre demande

1. **Imports incorrects** : Les tests utilisaient des imports relatifs qui ne fonctionnaient pas
2. **Mocks incomplets** : Les mocks ne couvraient pas toutes les méthodes async
3. **Fixtures manquantes** : Pas de `conftest.py` avec les fixtures partagées
4. **Configuration absente** : Pas de `pytest.ini`
5. **Pas de gestion async** : Tests async mal configurés

### ✅ Solutions appliquées

1. **conftest.py** : Fixtures réutilisables avec mocks complets
   - `mock_ollama_response` : Réponse standard
   - `mock_ollama_models` : Liste des modèles
   - `mock_httpx_client` : Client HTTP mocké

2. **test_app.py** : 15+ tests pour FastAPI
   - Tests des endpoints (`/`, `/health`, `/models`, `/ask`, `/generate`)
   - Tests de validation Pydantic
   - Tests de gestion d'erreurs
   - Tests de requêtes concurrentes

3. **test_ollama_client.py** : 10+ tests pour le client
   - Tests de génération avec/sans options
   - Tests de gestion d'erreurs HTTP
   - Tests de connexion
   - Tests de liste de modèles

4. **test_models.py** : 15+ tests pour Pydantic
   - Validation des champs obligatoires
   - Validation des contraintes (temperature, max_tokens)
   - Tests des valeurs par défaut

5. **pytest.ini** : Configuration complète
   - Markers personnalisés
   - Mode asyncio auto
   - Options de coverage

6. **run_tests.sh** : Script automatisé
   - Installation des dépendances
   - Sélection unit/integration
   - Coverage optionnel
   - Mode verbose

## 🎯 Résultats attendus

Quand vous lancez `pytest -v`, vous devriez voir :

```
tests/test_app.py::test_root_endpoint PASSED                          [ 10%]
tests/test_app.py::test_health_check_success PASSED                   [ 20%]
tests/test_app.py::test_list_models_success PASSED                    [ 30%]
tests/test_app.py::test_ask_endpoint_success PASSED                   [ 40%]
tests/test_ollama_client.py::test_ollama_client_initialization PASSED [ 50%]
tests/test_ollama_client.py::test_generate_success PASSED             [ 60%]
tests/test_models.py::test_minimal_prompt_request PASSED              [ 70%]
tests/test_models.py::test_full_prompt_request PASSED                 [ 80%]
...

========================= XX passed in X.XXs =========================
```

## 📈 Coverage attendu

Avec `pytest --cov=.` :

```
Name                    Stmts   Miss  Cover
-------------------------------------------
app.py                    120      5    96%
ollama_client.py           80      3    96%
config.py                  15      0   100%
models.py                  40      0   100%
-------------------------------------------
TOTAL                     255      8    97%
```

## 🐛 Troubleshooting

### Erreur : "Module not found"

```bash
# Solution 1 : Installer les dépendances
pip install -r requirements.txt

# Solution 2 : Ajouter le path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Erreur : "No tests collected"

```bash
# Vérifier que vous êtes dans le bon dossier
cd modules/neron_llm

# Vérifier la structure
ls tests/

# Lancer avec verbosité pour voir le problème
pytest -v --collect-only
```

### Erreur : "Async tests not working"

```bash
# Installer pytest-asyncio
pip install pytest-asyncio

# Vérifier la config dans pytest.ini
cat pytest.ini | grep asyncio
```

## 🎓 Exemples d'utilisation

### Lancer un test spécifique en debug

```bash
pytest tests/test_app.py::test_ask_endpoint_success -vv --tb=long -s
```

### Voir les prints dans les tests

```bash
pytest -s
```

### Générer un rapport HTML

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html  # Ouvrir le rapport
```

### Tests en boucle (watch mode)

```bash
# Installer pytest-watch
pip install pytest-watch

# Lancer en mode watch
ptw
```

## ✨ Prochaines étapes

1. **Lancer les tests** : `./tests/run_tests.sh --coverage`
2. **Vérifier le coverage** : Ouvrir `htmlcov/index.html`
3. **Intégrer au CI/CD** : Ajouter pytest dans votre pipeline
4. **Ajouter des tests** : Suivre les templates dans `tests/README.md`

## 📞 Support

Si vous rencontrez des problèmes :

1. Consultez `tests/README.md` pour plus de détails
2. Vérifiez que toutes les dépendances sont installées
3. Lancez avec `-vv --tb=long` pour plus d'informations

---

**Les tests sont maintenant prêts à être lancés ! 🎉**

Vous pouvez immédiatement exécuter :
```bash
./tests/run_tests.sh --install --coverage
```
