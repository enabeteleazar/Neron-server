# Changelog - Néron LLM

## [1.0.0] - 2025-02-11

### 🎉 Refonte complète du module

#### ✨ Nouveautés
- Nouvelle architecture avec wrapper HTTP autour d'Ollama
- Support complet de async/await
- Client HTTP httpx pour communiquer avec Ollama
- Modèles Pydantic pour validation des données
- Configuration centralisée avec pydantic-settings
- Health checks détaillés avec état de connexion Ollama
- Endpoint pour lister les modèles disponibles
- Gestion d'erreurs complète avec codes HTTP appropriés
- Tests unitaires avec pytest
- Documentation complète (README, MIGRATION)
- Docker Compose dédié pour tests indépendants
- Script d'initialisation des modèles

#### 🔧 Améliorations
- **Performance** : Utilisation de l'API HTTP au lieu de subprocess CLI
- **Maintenabilité** : Code structuré avec séparation des responsabilités
- **Fiabilité** : Gestion d'erreurs robuste avec retry et timeout
- **Observabilité** : Logging détaillé et métriques de génération
- **Testabilité** : Tests unitaires et fixtures pour mocking

#### 🔴 Breaking Changes
- Port changé de 11434 à 5000
- API complètement refaite (endpoints et modèles)
- Client Ollama maintenant asynchrone
- Configuration via variables d'environnement

#### 📝 Fichiers ajoutés
- `config.py` - Configuration centralisée
- `models.py` - Modèles Pydantic
- `ollama_client.py` - Client HTTP complet
- `__init__.py` - Exports du module
- `.env.example` - Template de configuration
- `docker-compose.yaml` - Tests indépendants
- `init_models.sh` - Initialisation des modèles
- `tests/test_app.py` - Tests unitaires
- `README.md` - Documentation détaillée
- `MIGRATION.md` - Guide de migration
- `CHANGELOG.md` - Ce fichier

#### 🗑️ Fichiers obsolètes
- Aucun fichier supprimé mais `ollama_client.py` complètement réécrit

#### 🐛 Corrections
- Correction de l'import manquant `subprocess` dans app.py
- Correction de l'URL Ollama incorrecte
- Correction de l'incohérence des ports
- Correction de la gestion d'erreurs basique

---

## [0.2.0] - Date inconnue

### État précédent
- Service FastAPI basique
- Utilisation de subprocess pour appeler le CLI Ollama
- Pas de gestion d'erreurs
- Pas de tests
- Configuration minimale
- Port 11434 ou 5000 (incohérent)

### Problèmes connus
- Import subprocess manquant
- Approche CLI non optimale
- Pas de validation des données
- Gestion d'erreurs insuffisante
- Pas de tests
- Documentation minimale

---

## [0.1.0] - Date inconnue

### État initial
- Fichier placeholder uniquement
- Aucune implémentation

---

## Notes de version

### Migration depuis v0.2.0
Voir le fichier `MIGRATION.md` pour un guide détaillé de migration.

### Compatibilité
- Python 3.11+
- FastAPI 0.109+
- Ollama API compatible

### Roadmap v1.1.0
- [ ] Support du streaming de réponses
- [ ] Cache des réponses avec Redis
- [ ] Métriques Prometheus
- [ ] Support de plusieurs backends LLM
- [ ] Rate limiting
- [ ] Authentication API
