# 🧠 Néron AI - Assistant IA Modulaire

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/yourusername/neron-ai)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)

Néron AI est un assistant IA modulaire et open-source construit sur une architecture microservices. Il combine reconnaissance vocale (STT), modèles de langage locaux (LLM via Ollama), mémoire persistante et une interface web intuitive.

## ✨ Fonctionnalités

- 🎤 **Speech-to-Text (STT)** - Transcription audio avec Whisper
- 🤖 **LLM Local** - Génération de texte avec Ollama (Llama, Mistral, etc.)
- 💾 **Mémoire Persistante** - Base de données SQLite pour l’historique
- 🌐 **Interface Web** - Interface utilisateur avec Gradio
- 🐳 **Architecture Microservices** - Services Docker indépendants
- 🔌 **API REST** - Intégration facile avec d’autres systèmes

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Néron AI System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐         │
│  │  Web UI  │──────│   Core   │──────│   STT    │         │
│  │ (Gradio) │      │(Orchestr)│      │(Whisper) │         │
│  │  :7860   │      │  :8000   │      │  :8001   │         │
│  └──────────┘      └──────────┘      └──────────┘         │
│                          │                                  │
│                    ┌─────┴─────┐                           │
│                    │           │                           │
│              ┌─────▼────┐ ┌───▼──────┐                    │
│              │   LLM    │ │  Memory  │                    │
│              │(Wrapper) │ │ (SQLite) │                    │
│              │  :5000   │ │  :8002   │                    │
│              └────┬─────┘ └──────────┘                    │
│                   │                                         │
│              ┌────▼─────┐                                  │
│              │  Ollama  │                                  │
│              │ (Engine) │                                  │
│              │  :11434  │                                  │
│              └──────────┘                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Modules

### Core Services

|Module          |Description                                      |Port |Technologie     |
|----------------|-------------------------------------------------|-----|----------------|
|**neron_core**  |Orchestrateur central, gère le flux de traitement|8000 |FastAPI         |
|**neron_llm**   |Wrapper HTTP autour d’Ollama                     |5000 |FastAPI, httpx  |
|**neron_stt**   |Service de transcription audio                   |8001 |FastAPI, Whisper|
|**neron_memory**|Stockage persistant des conversations            |8002 |FastAPI, SQLite |
|**neron_web**   |Interface utilisateur web                        |7860 |Gradio          |
|**neron_ollama**|Moteur LLM (Llama, Mistral, etc.)                |11434|Ollama          |

## 🚀 Installation Rapide

### Prérequis

- **Docker** 20.10+ et **Docker Compose** 2.0+
- **Git**
- **8 GB RAM** minimum (16 GB recommandé)
- **20 GB d’espace disque** pour les modèles LLM

### Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/yourusername/neron-ai.git
cd neron-ai

# 2. Créer le réseau Docker
docker network create Neron_Network

# 3. Copier et configurer les variables d'environnement
cp .env.example /opt/Homebox_AI/.env
nano /opt/Homebox_AI/.env

# 4. Lancer tous les services
./start_neron.sh

# 5. Télécharger un modèle LLM
docker exec -it neron_ollama ollama pull llama3.2:1b
```

### Vérification

```bash
# Vérifier que tous les services sont en cours d'exécution
docker compose ps

# Tester l'API Core
curl http://localhost:8000/health

# Tester l'interface web
# Ouvrir http://localhost:7860 dans votre navigateur
```

## 📖 Guide de Démarrage

### 1. Configuration Minimale

Créez un fichier `.env` avec les paramètres essentiels :

```bash
# Ports des services
NERON_CORE_HTTP=8000
NERON_STT_HTTP=8001
NERON_MEMORY_HTTP=8002
NERON_LLM_HTTP=11434

# Chemins
DOCKER_DATA_PATH=/opt/Homebox_AI/Data

# Modèles
OLLAMA_MODEL=llama3.2:1b
WHISPER_MODEL=base

# Timeouts
STT_TIMEOUT=30
LLM_TIMEOUT=60
MEMORY_TIMEOUT=5

# Logging
LOG_LEVEL=INFO
```

### 2. Premiers Pas

**Via l’interface web :**

```
1. Ouvrir http://localhost:7860
2. Taper votre message dans le champ de texte
3. Cliquer sur "Submit"
```

**Via l’API :**

```bash
curl -X POST http://localhost:8000/input/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour, comment vas-tu ?"}'
```

**Résultat :**

```json
{
  "response": "Je vais bien, merci ! Comment puis-je vous aider ?",
  "metadata": {
    "model": "llama3.2:1b"
  }
}
```

### 3. Utilisation Avancée

**Recherche dans la mémoire :**

```bash
curl "http://localhost:8002/search?query=météo&limit=5"
```

**Statistiques de la mémoire :**

```bash
curl http://localhost:8002/stats
```

**Lister les modèles disponibles :**

```bash
curl http://localhost:5000/models
```

## 🔧 Configuration Avancée

### Variables d’Environnement Complètes

Voir [`.env.example`](.env.example) pour la liste complète des variables.

### Personnalisation des Modèles

**Modèles LLM supportés :**

- Llama 3.2 (1B, 3B)
- Mistral (7B)
- Phi-3
- Gemma

**Télécharger un modèle :**

```bash
docker exec -it neron_ollama ollama pull mistral
```

**Changer le modèle par défaut :**

```bash
# Dans .env
OLLAMA_MODEL=mistral
```

### Ajuster les Performances

**Pour des réponses plus rapides (mais moins précises) :**

```bash
OLLAMA_MODEL=llama3.2:1b
WHISPER_MODEL=tiny
```

**Pour des réponses plus précises (mais plus lentes) :**

```bash
OLLAMA_MODEL=mistral:7b
WHISPER_MODEL=medium
```

## 🧪 Tests

### Tests Unitaires

```bash
# Tests du module LLM
cd modules/neron_llm
./tests/run_tests.sh --coverage

# Tests du module Core
cd modules/neron_core
pytest -v

# Tests de tous les modules
./run_all_tests.sh
```

### Tests d’Intégration

```bash
# Tester le pipeline complet
./scripts/integration_test.sh
```

## 📊 Monitoring et Logs

### Visualiser les Logs

```bash
# Tous les services
docker compose logs -f

# Un service spécifique
docker compose logs -f neron_core
docker compose logs -f neron_llm
docker compose logs -f neron_memory

# Logs avec horodatage
docker compose logs -f --timestamps
```

### Health Checks

```bash
# Vérifier l'état de tous les services
./scripts/health_check.sh

# Ou manuellement
curl http://localhost:8000/health  # Core
curl http://localhost:8001/health  # STT
curl http://localhost:8002/health  # Memory
curl http://localhost:5000/health  # LLM
```

## 🛠️ Maintenance

### Sauvegarde de la Mémoire

```bash
# Sauvegarder la base de données
docker cp neron_memory:/data/memory.db ./backups/memory_$(date +%Y%m%d).db
```

### Nettoyage

```bash
# Arrêter tous les services
docker compose down

# Supprimer les volumes (⚠️ perte de données)
docker compose down -v

# Nettoyer les images
docker system prune -a
```

### Mise à Jour

```bash
# Récupérer les dernières modifications
git pull origin main

# Reconstruire les images
docker compose build --no-cache

# Redémarrer les services
docker compose up -d
```

## 🐛 Dépannage

### Problèmes Courants

**Service ne démarre pas :**

```bash
# Vérifier les logs
docker compose logs [service_name]

# Vérifier les ports disponibles
netstat -tuln | grep [PORT]

# Reconstruire le conteneur
docker compose up -d --build [service_name]
```

**LLM trop lent :**

```bash
# Utiliser un modèle plus petit
docker exec -it neron_ollama ollama pull llama3.2:1b

# Ou augmenter les ressources Docker
# Docker Desktop > Settings > Resources
```

**Erreur de mémoire :**

```bash
# Augmenter la RAM allouée à Docker
# Minimum 8 GB, recommandé 16 GB
```

**Problèmes de réseau :**

```bash
# Recréer le réseau
docker network rm Neron_Network
docker network create Neron_Network
docker compose up -d
```

## 📚 Documentation

- [Guide d’Installation Détaillé](docs/INSTALLATION.md)
- [Architecture Technique](docs/ARCHITECTURE.md)
- [API Documentation](docs/API.md)
- [Guide de Contribution](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [FAQ](docs/FAQ.md)

### Documentation par Module

- [Néron Core](modules/neron_core/README.md)
- [Néron LLM](modules/neron_llm/docs/README.md)
- [Néron STT](modules/neron_stt/README.md)
- [Néron Memory](modules/neron_memory/README.md)
- [Néron Web](modules/neron_web/README.md)

## 🤝 Contribution

Les contributions sont les bienvenues ! Consultez <CONTRIBUTING.md> pour les guidelines.

### Workflow de Contribution

1. Fork le projet
1. Créer une branche feature (`git checkout -b feature/amazing-feature`)
1. Commit vos changements (`git commit -m 'Add amazing feature'`)
1. Push vers la branche (`git push origin feature/amazing-feature`)
1. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir <LICENSE> pour plus de détails.

## 👥 Auteurs

- **Néron AI Team** - *Développement initial*

## 🙏 Remerciements

- [Ollama](https://ollama.ai/) - Moteur LLM local
- [OpenAI Whisper](https://github.com/openai/whisper) - Modèle STT
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web
- [Gradio](https://gradio.app/) - Interface utilisateur
- La communauté open-source

## 📞 Support

- 🐛 **Issues** : [GitHub Issues](https://github.com/yourusername/neron-ai/issues)
- 💬 **Discussions** : [GitHub Discussions](https://github.com/yourusername/neron-ai/discussions)
- 📧 **Email** : support@neron-ai.example.com

## 🗺️ Roadmap

- [ ] Support du streaming pour les réponses LLM
- [ ] Intégration avec Home Assistant
- [ ] Support multi-utilisateurs
- [ ] Interface mobile
- [ ] Plugins extensibles
- [ ] Support de modèles TTS (Text-to-Speech)
- [ ] Intégration RAG (Retrieval-Augmented Generation)
- [ ] API GraphQL

## ⭐ Star History

Si vous trouvez ce projet utile, n’hésitez pas à lui donner une étoile !

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/neron-ai&type=Date)](https://star-history.com/#yourusername/neron-ai&Date)

-----

**Fait avec ❤️ par l’équipe Néron AI**
