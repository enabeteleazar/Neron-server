# 🧠 Néron AI - Assistant IA Modulaire

[![Version](https://img.shields.io/badge/version-1.6.0-blue.svg)](https://github.com/yourusername/neron-ai)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-68%20passed-brightgreen.svg)]()

Néron AI est un assistant IA modulaire et open-source construit sur une architecture microservices. Il combine reconnaissance vocale (STT), synthèse vocale (TTS), modèles de langage locaux (LLM via Ollama), recherche web locale, mémoire persistante et une interface web intuitive — le tout en **100% local, sans cloud**.

-----

## ✨ Fonctionnalités

- 🎤 **Speech-to-Text (STT)** — Transcription audio avec faster-whisper (int8, CPU-optimisé)
- 🔊 **Text-to-Speech (TTS)** — Synthèse vocale avec pyttsx3 (adapter pattern, extensible)
- 🤖 **LLM Local** — Génération de texte avec Ollama (llama3.2:3b par défaut)
- 🔍 **Recherche Web Locale** — SearXNG intégré, 100% offline
- 💾 **Mémoire Persistante** — Base de données SQLite pour l’historique des conversations
- 🌐 **Interface Web** — Interface utilisateur avec Gradio
- 🐳 **Architecture Microservices** — Services Docker indépendants et isolés
- 🔌 **API REST** — Endpoints texte, audio et vocal complet
- 📊 **Observabilité** — Métriques Prometheus sur `/metrics`
- 🔒 **Isolation Réseau** — Réseau Docker interne, surface d’attaque minimale

-----

## 🏗️ Architecture

```
Internet
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│  neron_core :8000  (orchestrateur, seul point d'entrée API)  │
│  neron_web  :7860  (interface Gradio)                        │
└─────────────────────────┬────────────────────────────────────┘
                          │
               neron_internal (bridge, isolé)
                          │
         ┌────────────────┼─────────────────┐
         │                │                 │
    ┌────▼─────┐   ┌──────▼──────┐   ┌──────▼─────┐
    │neron_stt │   │  neron_tts  │   │ neron_llm  │
    │  :8001   │   │   :8003     │   │   :5000    │
    │faster-   │   │   pyttsx3   │   │  wrapper   │
    │whisper   │   │             │   │  Ollama    │
    └──────────┘   └─────────────┘   └──────┬─────┘
                                             │
    ┌─────────────┐                   ┌──────▼──────┐
    │neron_memory │                   │neron_ollama │
    │   :8002     │                   │   :11434    │
    │   SQLite    │                   │llama3.2:3b  │
    └─────────────┘                   └─────────────┘
    ┌─────────────┐
    │neron_searxng│
    │   :8080     │
    │   SearXNG   │
    └─────────────┘
```

### Pipelines disponibles

```
POST /input/text
  → texte → intent router → LLM / time_provider / web → CoreResponse (JSON)

POST /input/audio
  → audio → STT → texte → intent router → LLM / time_provider / web → CoreResponse (JSON)

POST /input/voice
  → audio → STT → texte → intent router → LLM / time_provider / web → TTS → audio WAV
```

### Intent Router

|Intent        |Déclencheur                     |Agent                      |Latence |
|--------------|--------------------------------|---------------------------|--------|
|`time_query`  |“heure”, “date”, “jour”         |time_provider              |~0.3ms  |
|`web_search`  |“cherche”, “météo”, “news”      |web_agent + SearXNG        |~2s     |
|`ha_action`   |“allume”, “éteins”, “thermostat”|*(home assistant, à venir)*|—       |
|`conversation`|tout le reste                   |llm_agent                  |~86s CPU|

-----

## 📦 Services

|Service          |Description                                    |Port |Technologie              |
|-----------------|-----------------------------------------------|-----|-------------------------|
|**neron_core**   |Orchestrateur central, intent router, pipelines|8000 |FastAPI                  |
|**neron_stt**    |Transcription audio                            |8001 |faster-whisper 1.0.3 int8|
|**neron_memory** |Mémoire persistante conversations              |8002 |FastAPI, SQLite          |
|**neron_tts**    |Synthèse vocale                                |8003 |pyttsx3, adapter pattern |
|**neron_llm**    |Wrapper HTTP Ollama                            |5000 |FastAPI, httpx           |
|**neron_ollama** |Moteur LLM                                     |11434|Ollama                   |
|**neron_searxng**|Recherche web locale                           |8080 |SearXNG                  |
|**neron_web**    |Interface utilisateur                          |7860 |Gradio                   |

-----

## 🚀 Installation Rapide

### Prérequis

- **Docker** 20.10+ et **Docker Compose** 2.0+
- **Git**
- **8 GB RAM** minimum (16 GB recommandé pour llama3.2:3b)
- **20 GB d’espace disque** pour les modèles

### Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/yourusername/neron-ai.git
cd neron-ai

# 2. Créer le réseau Docker externe
docker network create Neron_Network

# 3. Configurer les variables d'environnement
cp .env.example /opt/Neron_AI/.env
nano /opt/Neron_AI/.env

# 4. Lancer tous les services
docker compose --env-file /opt/Neron_AI/.env up -d

# 5. Télécharger le modèle LLM
docker exec neron_ollama ollama pull llama3.2:3b
```

### Vérification

```bash
# Vérifier tous les services
docker compose ps

# Health checks manuels
curl http://localhost:8000/health  # Core
curl http://localhost:7860         # Interface web

# Métriques Prometheus
curl http://localhost:8000/metrics
```

-----

## 📖 API

### GET /health

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "version": "1.6.0"
}
```

### GET /metrics

Métriques Prometheus :

```
neron_uptime_seconds
neron_requests_total
neron_requests_in_flight
neron_execution_time_avg_ms
neron_intent_total{intent="time_query"}
neron_agent_errors_total{agent="llm_agent"}
neron_agent_latency_avg_ms{agent="stt_agent"}
```

### POST /input/text — Pipeline texte

```bash
curl -X POST http://localhost:8000/input/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Quelle heure est-il ?"}'
```

```json
{
  "response": "Il est samedi 22 février 2026 à 00h30.",
  "intent": "time_query",
  "agent": "time_provider",
  "confidence": "high",
  "timestamp": "2026-02-22T00:30:00+00:00",
  "execution_time_ms": 0.32,
  "model": null,
  "error": null
}
```

### POST /input/audio — Pipeline audio (STT → texte)

```bash
curl -X POST http://localhost:8000/input/audio \
  -F "file=@/chemin/vers/audio.wav"
```

```json
{
  "response": "Il est samedi 22 février 2026 à 00h30.",
  "intent": "time_query",
  "agent": "time_provider",
  "transcription": "Bonjour Neron quelle heure est il",
  "metadata": {
    "stt": {
      "language": "fr",
      "stt_model": "base",
      "stt_latency_ms": 7863.0
    }
  }
}
```

### POST /input/voice — Pipeline vocal complet (STT → LLM → TTS)

```bash
curl -X POST http://localhost:8000/input/voice \
  -F "file=@/chemin/vers/audio.wav" \
  -o reponse.wav
```

Retourne un fichier **audio/wav** avec headers :

```
X-Transcription: Bonjour Neron quelle heure est il
X-Response-Text: Il est samedi 22 février 2026 à 00h30.
X-Intent: time_query
X-Execution-Time-Ms: 9200.5
X-STT-Latency-Ms: 7863.0
X-TTS-Latency-Ms: 312.4
```

-----

## ⚙️ Configuration

### Variables d’environnement principales

```bash
# Ports
NERON_CORE_HTTP=8000
NERON_STT_HTTP=8001
NERON_MEMORY_HTTP=8002

# URLs internes (Docker)
NERON_STT_URL=http://neron_stt:8001
NERON_LLM_URL=http://neron_llm:5000
NERON_MEMORY_URL=http://neron_memory:8002
NERON_TTS_URL=http://neron_tts:8003

# LLM
OLLAMA_MODEL=llama3.2:3b
LLM_TIMEOUT=120

# STT
WHISPER_MODEL=base
WHISPER_LANGUAGE=fr
AUDIO_MAX_SIZE_MB=10
STT_TIMEOUT=60

# TTS
TTS_ENGINE=pyttsx3
TTS_LANGUAGE=fr
TTS_RATE=150
TTS_MAX_CHARS=1000

# Général
LOG_LEVEL=INFO
DOCKER_DATA_PATH=/opt/Neron_AI/Data
```

### Choisir le bon modèle LLM

|Modèle       |Latence CPU|Qualité français|RAM |
|-------------|-----------|----------------|----|
|`llama3.2:1b`|~38s       |⚠️ faible        |2 GB|
|`llama3.2:3b`|~86s       |✅ bonne         |4 GB|
|`orca-mini`  |~62s       |⚠️ mélange fr/en |4 GB|

```bash
# Changer le modèle
docker exec neron_ollama ollama pull llama3.2:1b
# Puis dans .env : OLLAMA_MODEL=llama3.2:1b
docker compose up -d neron_core
```

### Choisir le modèle Whisper

|Modèle |Latence|Précision      |
|-------|-------|---------------|
|`tiny` |~3s    |faible         |
|`base` |~8s    |✅ bon compromis|
|`small`|~15s   |meilleure      |

-----

## 🧪 Tests

```bash
# Lancer tous les tests
cd /chemin/vers/neron-ai
pytest modules/neron_core -v

# Résultat attendu
# 68 passed in ~1.5s
```

### Couverture des tests

|Fichier de test        |Tests |Couvre                            |
|-----------------------|------|----------------------------------|
|`test_core_response.py`|8     |CoreResponse, timestamps, metadata|
|`test_orchestrator.py` |7     |IntentRouter, enum, valeurs       |
|`test_router.py`       |12    |Classification intents            |
|`test_stt_agent.py`    |11    |STTAgent, formats, erreurs        |
|`test_tts_agent.py`    |9     |TTSAgent, synthèse, erreurs       |
|`test_time_provider.py`|15    |TimeProvider, formats             |
|`test_web_agent.py`    |6     |WebAgent, SearXNG, erreurs        |
|**Total**              |**68**|                                  |

-----

## 📊 Performances (CPU-only)

|Composant                      |Latence |Notes              |
|-------------------------------|--------|-------------------|
|time_provider                  |~0.3ms  |Sans LLM           |
|neron_stt (faster-whisper int8)|~8s     |Voix humaine réelle|
|neron_tts (pyttsx3)            |~300ms  |                   |
|neron_llm (llama3.2:3b)        |~86s    |CPU-bound          |
|**Pipeline vocal complet**     |**~95s**|STT + LLM + TTS    |


> **Note :** Les performances LLM sont contraintes par le CPU. Sur GPU, llama3.2:3b descend à ~2s.

-----

## 🛠️ Maintenance

### Logs

```bash
# Tous les services
docker compose logs -f

# Un service spécifique
docker compose logs -f neron_core
docker compose logs -f neron_stt
docker compose logs -f neron_tts
```

### Sauvegarde mémoire

```bash
docker cp neron_memory:/data/memory.db ./backups/memory_$(date +%Y%m%d).db
```

### Mise à jour

```bash
git pull origin main
docker compose build --no-cache
docker compose up -d
```

### Nettoyage

```bash
# Arrêter
docker compose down

# Arrêter et supprimer les volumes (⚠️ perte de données)
docker compose down -v
```

-----

## 🐛 Dépannage

### Service ne démarre pas

```bash
docker compose logs [service]
docker compose up -d --build [service]
```

### LLM trop lent

```bash
# Utiliser un modèle plus léger
OLLAMA_MODEL=llama3.2:1b
```

### STT transcription incorrecte

```bash
# Vérifier la langue
WHISPER_LANGUAGE=fr

# Utiliser un modèle plus précis
WHISPER_MODEL=small
```

### Réseau introuvable

```bash
docker network create Neron_Network
docker compose up -d
```

-----

## 🗺️ Roadmap

- [x] Pipeline texte (v1.1.0)
- [x] Mémoire persistante SQLite (v1.2.0)
- [x] Intent router + WebAgent + SearXNG (v1.3.0)
- [x] TimeProvider, métriques Prometheus (v1.4.0)
- [x] Pipeline audio STT faster-whisper (v1.5.0)
- [x] Pipeline vocal complet STT + TTS (v1.6.0)
- [ ] File d’attente requêtes (Semaphore) (v1.7.0)
- [ ] Intégration Home Assistant (v2.0.0)
- [ ] Streaming STT via WebSocket (v2.1.0)
- [ ] Support GPU (v2.2.0)
- [ ] RAG — Retrieval-Augmented Generation (v3.0.0)

-----

## 📚 Documentation

- [CHANGELOG](CHANGELOG.md)
- [Néron LLM](modules/neron_llm/docs/README.md)

-----

## 📄 Licence

Ce projet est sous licence MIT.

-----

## 🙏 Remerciements

- [Ollama](https://ollama.ai/) — Moteur LLM local
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — STT optimisé CPU
- [SearXNG](https://searxng.github.io/searxng/) — Moteur de recherche local
- [FastAPI](https://fastapi.tiangolo.com/) — Framework web
- [Gradio](https://gradio.app/) — Interface utilisateur
- [pyttsx3](https://pyttsx3.readthedocs.io/) — TTS offline

-----

**Fait avec ❤️ — Néron AI v1.6.0**
