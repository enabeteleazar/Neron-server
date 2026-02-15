# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.2.2/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié](https://github.com/yourusername/neron-ai/compare/v1.2.2...HEAD)

### À venir

- Support du streaming pour les réponses LLM
- Intégration avec Home Assistant
- Support multi-utilisateurs
- Interface mobile native
- Plugins extensibles
- Support TTS (Text-to-Speech)

-----

## [1.2.2](https://github.com/yourusername/neron-ai/releases/tag/v1.2.2) - 2025-02-15

### 🎉 Version Initiale de Production

Première version stable et complète de Néron AI avec architecture microservices.

### ✨ Ajouts

#### Architecture

- Architecture microservices avec Docker Compose
- Réseau Docker dédié `Neron_Network`
- Health checks pour tous les services
- Gestion automatique des dépendances entre services
- Scripts de démarrage automatisés

#### Modules Core

**neron_core (v0.2.0)**

- Orchestrateur central avec FastAPI
- Pipeline de traitement : Texte → LLM → Mémoire
- API REST complète
- Gestion d’erreurs robuste avec codes HTTP appropriés
- Logging structuré
- Timeouts configurables
- Support async/await

**neron_llm (v1.2.2)**

- Wrapper HTTP autour d’Ollama
- Client HTTP asynchrone avec httpx
- Support de tous les modèles Ollama (Llama, Mistral, etc.)
- Configuration centralisée avec pydantic-settings
- Gestion de contexte de conversation
- Métriques de génération (tokens, temps)
- Validation des paramètres avec Pydantic
- 40+ tests unitaires avec 95%+ coverage
- Documentation complète

**neron_stt (v0.1.0)**

- Service de transcription audio avec Whisper
- Support des formats : WAV, MP3, M4A, OGG
- API REST avec endpoint `/speech`
- Gestion de fichiers temporaires sécurisée
- Modèle configurable (tiny, base, small, medium, large)

**neron_memory (v0.2.0)**

- Base de données SQLite persistante
- Stockage des conversations avec métadonnées
- API de recherche full-text
- Statistiques de l’historique
- Endpoints : store, retrieve, search, stats, clear
- Indices de performance
- Gestion thread-safe des connexions

**neron_web (v0.1.0)**

- Interface utilisateur avec Gradio 4.16
- Chat interface intuitive
- Connexion au service Core
- Gestion d’erreurs utilisateur
- Thème personnalisé

**neron_ollama**

- Intégration Ollama officielle (image `ollama/ollama:latest`)
- Support des modèles : Llama 3.2, Mistral, Phi-3, Gemma
- Persistance des modèles avec volumes Docker
- API HTTP sur port 11434

#### Configuration

- Fichier `.env.example` avec documentation complète
- Variables d’environnement pour tous les modules
- Configuration des timeouts personnalisables
- Configuration des niveaux de log
- Configuration des chemins de données
- Support de différents environnements (dev/prod)

#### Scripts et Outils

- `start_neron.sh` - Script de démarrage avec interface colorée
- `docker-compose.yaml` - Orchestration complète
- Health check automatiques
- Restart policies configurées
- Scripts d’initialisation des modèles

#### Documentation

- README principal complet
- Documentation par module
- Guides d’installation
- Guide de migration LLM v0.2 → v1.0
- Documentation API
- Guide de tests
- Exemples d’utilisation
- Troubleshooting

#### Tests

**Module neron_llm**

- 40+ tests unitaires
- Fixtures pytest partagées
- Tests d’API avec TestClient
- Tests du client Ollama avec mocks
- Tests de validation Pydantic
- Coverage > 95%
- CI/CD ready

#### Fichiers de Projet

- `.gitignore` complet (Python, Docker, Node, secrets)
- Structure de projet professionnelle
- Séparation claire des responsabilités
- Conventions de nommage cohérentes

### 🔧 Améliorations

#### Performance

- Utilisation de l’API HTTP Ollama au lieu de CLI (gain ~40%)
- Support async/await complet pour tous les services
- Connexions HTTP persistantes avec httpx
- Gestion efficace de la mémoire

#### Fiabilité

- Gestion d’erreurs complète avec retry
- Validation des données avec Pydantic
- Timeouts configurables
- Health checks détaillés
- Logging structuré

#### Maintenabilité

- Code modulaire et testé
- Documentation inline
- Type hints Python
- Configuration centralisée
- Séparation des concerns

#### Sécurité

- Pas de secrets en dur dans le code
- Variables d’environnement pour config sensible
- Utilisateurs non-root dans les conteneurs
- Isolation réseau avec Docker network

### 📝 Documentation

- README principal avec guide complet
- Documentation technique détaillée
- Exemples d’utilisation
- Guide de contribution
- Licence MIT
- Changelog structuré

### 🐛 Corrections

#### Module neron_llm

- Correction import `subprocess` manquant
- Correction URL Ollama incorrecte
- Correction incohérence des ports (5000 vs 11434)
- Correction gestion d’erreurs basique
- Correction imports relatifs pour tests

#### Module neron_core

- Correction gestion des timeouts
- Correction validation des réponses LLM
- Correction logging des erreurs

#### Infrastructure

- Correction dépendances entre services
- Correction health checks
- Correction restart policies

### 🔒 Sécurité

- Pas de credentials en clair
- Utilisation de variables d’environnement
- Isolation des services
- Validation des entrées utilisateur

### 📊 Métriques

- **Modules** : 6 services indépendants
- **Tests** : 40+ tests unitaires
- **Coverage** : > 95% pour neron_llm
- **Documentation** : 15+ fichiers de doc
- **API Endpoints** : 15+ endpoints REST

-----

## [0.2.0](https://github.com/yourusername/neron-ai/releases/tag/v0.2.0) - 2025-02-10

### Ajouts

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

## [0.1.0](https://github.com/yourusername/neron-ai/releases/tag/v0.1.0) - 2025-02-01

### Ajouts

- Structure de projet initiale
- Docker Compose basique
- Modules neron_core et neron_stt en développement

### Notes

- Version alpha, non stable
- Développement actif

-----

## Format des Entrées

### Types de Changements

- **✨ Ajouts** : Nouvelles fonctionnalités
- **🔧 Améliorations** : Améliorations de fonctionnalités existantes
- **🐛 Corrections** : Corrections de bugs
- **🔒 Sécurité** : Correctifs de sécurité
- **📝 Documentation** : Changements dans la documentation
- **🗑️ Suppressions** : Fonctionnalités supprimées
- **⚠️ Déprécié** : Fonctionnalités bientôt supprimées

### Versioning

- **MAJOR** (X.0.0) : Changements incompatibles avec l’API
- **MINOR** (0.X.0) : Nouvelles fonctionnalités rétrocompatibles
- **PATCH** (0.0.X) : Corrections de bugs rétrocompatibles

-----

## Liens

- 
- 
- 
- 
