# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.2.2/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié]

### A venir

- ha_agent.py : controle Home Assistant (v1.4.0)
- Redis Event Bus (remplacement REST interne)
- Support du streaming pour les réponses LLM
- Support multi-utilisateurs
- Interface mobile native
- Plugins extensibles
- Support TTS (Text-to-Speech)

-----

## [1.3.1] - 2025-02-19

### Corrections suite audit DevOps

#### Robustesse reseau

- `web_agent.py` : capture separee de chaque type d’erreur HTTP (TimeoutException, ConnectError, HTTPStatusError, RequestError)
- `llm_agent.py` : meme traitement, timeout granulaire via `httpx.Timeout`
- Fallback propre vers conversation si WebAgent indisponible

#### Architecture

- Router avec registre dynamique d’agents (`build_intent_registry`)
- Ajout de `meteo` sans accent dans les patterns du router (robustesse saisie utilisateur)
- Imports absolus partout, suppression des imports relatifs problematiques
- `__init__.py` vidés pour eviter les conflits de chargement pytest

#### Securite

- SearXNG : port 8888 supprime du docker-compose (reseau interne Docker uniquement)
- Dockerfile neron_core : user non-root `neron`
- Healthcheck SearXNG corrige avec `wget` (present dans l’image)

#### Observabilite

- JSON logging structure sur tous les composants (agents, router, app)
- Endpoint `/metrics` Prometheus sur neron_core (compteurs intents, erreurs, latences)
- Mesure de latence sur chaque AgentResult

#### Tests

- 22 tests pytest passes : 7 orchestrator, 9 router, 6 web_agent
- `conftest.py` avec fixtures partagees (mock_llm_success, mock_llm_failure, mock_searxng_response)
- `pytest.ini` configure avec asyncio_mode = auto

-----

## [1.3.0] - 2025-02-19

### Orchestrateur central - Neron Core

#### Nouveautes

- Neron Core devient un orchestrateur multi-agents
- `IntentRouter` : classification en deux passes (rules-based + LLM fallback)
- `BaseAgent` : classe abstraite commune, AgentResult standardise
- `LLMAgent` : wrapper neron_llm en tant qu’agent
- `WebAgent` : recherche web via SearXNG self-hosted
- Pipeline web : WebAgent -> resultats bruts -> LLMAgent synthese -> reponse
- Nouveau service `neron_searxng` dans docker-compose

#### Intents supportes

- `CONVERSATION` : reponse LLM directe
- `WEB_SEARCH` : recherche SearXNG + synthese LLM
- `HA_ACTION` : reserve v1.4.0, slot deja en place dans le router

#### Structure ajoutee dans neron_core

```
agents/
  base_agent.py
  llm_agent.py
  web_agent.py
orchestrator/
  intent_router.py
tests/
  conftest.py
  test_orchestrator.py
  test_router.py
  test_web_agent.py
```

#### CoreResponse enrichie

```json
{
  "response": "...",
  "intent": "web_search",
  "confidence": "high",
  "metadata": {
    "web_sources": ["url1", "url2"],
    "web_results_count": 12
  }
}
```

-----

## [1.2.2] - 2025-02-15

### Version Initiale de Production

Première version stable et complète de Néron AI avec architecture microservices.

#### Architecture

- Architecture microservices avec Docker Compose
- Réseau Docker dédié `Neron_Network`
- Health checks pour tous les services
- Gestion automatique des dépendances entre services
- Scripts de démarrage automatisés

#### Modules Core

**neron_core (v0.2.0)**

- Orchestrateur central avec FastAPI
- Pipeline de traitement : Texte -> LLM -> Mémoire
- API REST complète avec gestion d’erreurs robuste
- Logging structuré, timeouts configurables, support async/await

**neron_llm (v1.2.2)**

- Wrapper HTTP autour d’Ollama
- Client HTTP asynchrone avec httpx
- Support de tous les modèles Ollama (Llama, Mistral, etc.)
- Configuration centralisée avec pydantic-settings
- 40+ tests unitaires avec 95%+ coverage

**neron_stt (v0.1.0)**

- Service de transcription audio avec Whisper
- Support des formats : WAV, MP3, M4A, OGG
- API REST avec endpoint `/speech`

**neron_memory (v0.2.0)**

- Base de données SQLite persistante
- Stockage des conversations avec métadonnées
- API de recherche full-text
- Endpoints : store, retrieve, search, stats, clear

**neron_web (v0.1.0)**

- Interface utilisateur avec Gradio 4.16
- Chat interface intuitive connectée au service Core

**neron_ollama**

- Intégration Ollama officielle
- Support des modèles : Llama 3.2, Mistral, Phi-3, Gemma
- Persistance des modèles avec volumes Docker

#### Tests

- 40+ tests unitaires pour neron_llm
- Coverage > 95%
- CI/CD ready

#### Corrections

- Import `subprocess` manquant dans neron_llm
- URL Ollama incorrecte
- Incohérence des ports (5000 vs 11434)
- Gestion d’erreurs basique
- Health checks et restart policies

-----

## [0.2.0] - 2025-02-10

### Beta

- Version beta du module neron_core
- Version beta du module neron_memory
- Intégration basique avec Ollama
- Interface web Gradio basique

### Problèmes Connus

- Module neron_llm incomplet (placeholder)
- Pas de tests unitaires
- Documentation minimale
- Gestion d’erreurs basique
- Pas de health checks

-----

## [0.1.0] - 2025-02-01

### Alpha

- Structure de projet initiale
- Docker Compose basique
- Modules neron_core et neron_stt en développement
- Version alpha, non stable

-----

## Format des Entrées

- **Ajouts** : Nouvelles fonctionnalités
- **Améliorations** : Améliorations de fonctionnalités existantes
- **Corrections** : Corrections de bugs
- **Securite** : Correctifs de sécurité
- **Suppressions** : Fonctionnalités supprimées

## Versioning

- **MAJOR** (X.0.0) : Changements incompatibles avec l’API
- **MINOR** (0.X.0) : Nouvelles fonctionnalités rétrocompatibles
- **PATCH** (0.0.X) : Corrections de bugs rétrocompatibles
