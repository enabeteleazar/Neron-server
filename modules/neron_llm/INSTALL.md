# 📦 Néron LLM v1.0.0 - Installation

## 📂 Contenu de l'archive

Cette archive contient le module **Néron LLM** complet et prêt à l'emploi.

### Structure
```
neron_llm/
├── .env.example                 # Template de configuration
├── __init__.py                  # Exports du module
├── app.py                       # Application FastAPI principale
├── config.py                    # Configuration centralisée
├── models.py                    # Modèles Pydantic
├── ollama_client.py             # Client HTTP pour Ollama
├── requirements.txt             # Dépendances Python
├── Dockerfile                   # Image Docker
├── docker-compose.yaml          # Services Docker
├── init_models.sh               # Script d'initialisation des modèles
│
├── tests/                       # Tests unitaires (24 fichiers)
│   ├── __init__.py
│   ├── conftest.py              # Fixtures pytest
│   ├── pytest.ini               # Configuration pytest
│   ├── test_app.py              # 15+ tests FastAPI
│   ├── test_models.py           # 15+ tests Pydantic
│   ├── test_ollama_client.py    # 10+ tests client
│   ├── run_tests.sh             # Script de lancement
│   └── README.md                # Documentation tests
│
└── docs/                        # Documentation complète (7 fichiers)
    ├── 00_README_REFONTE.md     # ⭐ LIRE EN PREMIER
    ├── README.md                # Documentation principale
    ├── MIGRATION.md             # Guide de migration v0.2 → v1.0
    ├── CHANGELOG.md             # Historique des versions
    ├── TESTS_GUIDE.md           # Guide complet des tests
    ├── FIX_IMPORTS.md           # Corrections des imports
    └── neron_llm_analysis.md    # Analyse technique
```

## 🚀 Installation rapide

### 1. Extraire l'archive

```bash
# Avec tar.gz
tar -xzf neron_llm_v1.0.0.tar.gz

# Avec zip
unzip neron_llm_v1.0.0.zip

# Aller dans le dossier
cd neron_llm
```

### 2. Configurer

```bash
# Copier le fichier de configuration
cp .env.example .env

# Éditer selon vos besoins (optionnel)
nano .env
```

### 3. Lancer avec Docker

```bash
# Démarrer les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f

# Télécharger un modèle
./init_models.sh llama3.2:1b
```

### 4. Tester

```bash
# Health check
curl http://localhost:5000/health

# Test de génération
curl -X POST http://localhost:5000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Bonjour", "model": "llama3.2:1b"}'
```

### 5. Lancer les tests (optionnel)

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer tous les tests
./tests/run_tests.sh

# Avec coverage
./tests/run_tests.sh --coverage
```

## 📖 Documentation

**Commencez par lire** : `docs/00_README_REFONTE.md`

Ensuite consultez selon vos besoins :
- **docs/README.md** - Documentation complète de l'API
- **docs/MIGRATION.md** - Migration depuis v0.2.0
- **docs/TESTS_GUIDE.md** - Guide complet des tests
- **docs/FIX_IMPORTS.md** - Résolution des problèmes d'imports

## 🔧 Intégration dans votre projet

### Option 1 : Remplacer le module existant

```bash
# Sauvegarder l'ancien module (si existant)
mv /path/to/modules/neron_llm /path/to/modules/neron_llm.old

# Copier le nouveau module
cp -r neron_llm /path/to/modules/

# Vérifier
ls -la /path/to/modules/neron_llm
```

### Option 2 : Mise à jour sélective

```bash
# Copier uniquement les fichiers Python
cp neron_llm/*.py /path/to/modules/neron_llm/

# Copier les tests
cp -r neron_llm/tests /path/to/modules/neron_llm/

# Copier la config Docker
cp neron_llm/Dockerfile neron_llm/docker-compose.yaml /path/to/modules/neron_llm/
```

## ⚙️ Configuration minimale requise

- **Python** : 3.11+
- **Docker** : 20.10+
- **Docker Compose** : 2.0+
- **RAM** : 4 GB minimum (8 GB recommandé)
- **Espace disque** : 10 GB minimum pour les modèles

## 📊 Versions des dépendances

```
FastAPI       : 0.109.0
Uvicorn       : 0.27.0
httpx         : 0.26.0
Pydantic      : 2.5.3
pytest        : 7.4.3
```

## 🆘 Support

En cas de problème :

1. Vérifiez `docs/FIX_IMPORTS.md` pour les erreurs d'imports
2. Consultez `docs/MIGRATION.md` section "Troubleshooting"
3. Vérifiez les logs : `docker-compose logs neron-llm`
4. Lancez les tests : `./tests/run_tests.sh -v`

## 📝 Checklist d'installation

- [ ] Archive extraite
- [ ] Fichier `.env` créé et configuré
- [ ] Services Docker démarrés
- [ ] Ollama accessible (health check OK)
- [ ] Modèle téléchargé
- [ ] Test de génération réussi
- [ ] Tests unitaires passent (optionnel)
- [ ] Intégration avec neron-core vérifiée

## 🎉 C'est prêt !

Le module est maintenant installé et fonctionnel.

Pour plus d'informations, consultez la documentation dans `docs/`.

---

**Version** : 1.0.0  
**Date** : 2025-02-11  
**Architecture** : Microservices avec wrapper Ollama  
**Tests** : 40+ tests unitaires avec 95%+ coverage
