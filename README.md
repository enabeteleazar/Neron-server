# 🧠 Néron AI - Assistant IA Local

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/enabeteleazar/Neron_AI)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ollama](https://img.shields.io/badge/ollama-compatible-black.svg)](https://ollama.com/)

Néron AI est un assistant IA modulaire et open-source qui combine reconnaissance vocale (STT), synthèse vocale (TTS), modèles de langage locaux (LLM via Ollama), recherche web, mémoire persistante et bots Telegram — le tout en **1 seul processus Python, 100% local, sans cloud, sans Docker**.

-----

## ✨ Fonctionnalités

- 🎤 **Speech-to-Text (STT)** — Transcription audio avec faster-whisper (int8, CPU-optimisé)
- 🔊 **Text-to-Speech (TTS)** — Synthèse vocale avec pyttsx3 (adapter pattern, extensible)
- 🤖 **LLM Local** — Génération de texte avec Ollama (llama3.2 par défaut)
- 🔍 **Recherche Web** — Agent web intégré, 100% local
- 💾 **Mémoire Persistante** — SQLite pour l’historique des conversations
- 🤖 **Bots Telegram** — Deux bots bidirectionnels (commandes + notifications), optionnels
- 🐕 **Watchdog** — Supervision et restart automatique des agents, optionnel
- 🔌 **API REST** — Endpoints texte, audio et vocal complet
- 📊 **Observabilité** — Métriques Prometheus sur `/metrics`
- ⚙️ **Service systemd** — Démarrage automatique au boot, restart sur crash

-----

## 🏗️ Architecture

```
                    ┌─────────────────────────────────┐
                    │      neron_core :8000            │
                    │   (1 processus Python unique)    │
                    │                                  │
                    │  ┌──────────┐  ┌─────────────┐  │
                    │  │ llm_agent│  │  stt_agent  │  │
                    │  └────┬─────┘  └──────┬──────┘  │
                    │       │               │          │
                    │  ┌────▼─────┐  ┌──────▼──────┐  │
                    │  │  Ollama  │  │faster-whisper│  │
                    │  └──────────┘  └─────────────┘  │
                    │                                  │
                    │  ┌──────────┐  ┌─────────────┐  │
                    │  │ tts_agent│  │memory_agent │  │
                    │  └──────────┘  └─────────────┘  │
                    │                                  │
                    │  ┌───────────────┐               │
                    │  │telegram_agent │ (optionnel)   │
                    │  └───────────────┘               │
                    │  ┌───────────────┐               │
                    │  │watchdog_agent │ (optionnel)   │
                    │  └───────────────┘               │
                    └─────────────────────────────────┘
```

### Pipelines disponibles

```
POST /input/text
  → intent router → LLM / time_provider / web → CoreResponse (JSON)

POST /input/audio
  → STT → intent router → LLM / time_provider / web → CoreResponse (JSON)

POST /input/voice
  → STT → intent router → LLM / time_provider / web → TTS → audio WAV
```

### Intent Router

|Intent        |Déclencheur                     |Agent                      |Latence |
|--------------|--------------------------------|---------------------------|--------|
|`time_query`  |“heure”, “date”, “jour”         |time_provider              |~0.3ms  |
|`web_search`  |“cherche”, “météo”, “news”      |web_agent                  |~2s     |
|`ha_action`   |“allume”, “éteins”, “thermostat”|*(home assistant, à venir)*|—       |
|`conversation`|tout le reste                   |llm_agent                  |~86s CPU|

-----

## 📦 Agents

|Agent             |Description                       |Optionnel|
|------------------|----------------------------------|---------|
|**llm_agent**     |Génération LLM via Ollama         |Non      |
|**stt_agent**     |Transcription audio faster-whisper|Non      |
|**tts_agent**     |Synthèse vocale pyttsx3           |Non      |
|**memory_agent**  |Mémoire persistante SQLite        |Non      |
|**web_agent**     |Recherche web locale              |Non      |
|**time_provider** |Heure et date localisées          |Non      |
|**telegram_agent**|Bots Telegram bidirectionnels     |Oui      |
|**watchdog_agent**|Supervision et restart automatique|Oui      |

-----

## 🚀 Installation

### One-liner (recommandé)

```bash
curl -fsSL https://raw.githubusercontent.com/enabeteleazar/Neron_AI/master/install.sh | bash
```

Le script installe et configure tout automatiquement.

### Installation manuelle

```bash
# Cloner
git clone https://github.com/enabeteleazar/Neron_AI.git
cd Neron_AI

# Configurer
cp .env.example .env
nano .env

# Installer
make install

# Télécharger un modèle
make ollama

# Démarrer
make start
```

### Commandes disponibles

```bash
make start      # Démarrer Néron
make stop       # Arrêter
make restart    # Redémarrer
make status     # État des services
make logs       # Logs en temps réel
make update     # Mise à jour (git pull + restart)
make backup     # Sauvegarder les données
make restore    # Restaurer une sauvegarde
make test       # Lancer les tests
make ollama     # Gérer le modèle LLM
make telegram   # Configurer les bots Telegram
make env        # Afficher la configuration active
make version    # Version installée
make clean      # Nettoyer les fichiers temporaires
```

### Vérification

```bash
make status
# ou
curl http://localhost:8000/health
# {"status": "healthy", "version": "2.0.0"}
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
  "version": "2.0.0"
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
  -H "X-API-Key: votre_api_key" \
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

### POST /input/audio — Pipeline audio (STT → LLM)

```bash
curl -X POST http://localhost:8000/input/audio \
  -H "X-API-Key: votre_api_key" \
  -F "file=@audio.wav"
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
  -H "X-API-Key: votre_api_key" \
  -F "file=@audio.wav" \
  -o reponse.wav
```

Retourne un fichier **audio/wav** avec headers :

```
X-Transcription      — texte reconnu
X-Response-Text      — réponse de Néron
X-Intent             — intent détecté
X-Execution-Time-Ms  — temps total
X-STT-Latency-Ms     — latence STT
X-TTS-Latency-Ms     — latence TTS
```

-----

## ⚙️ Configuration

### Variables d’environnement principales

```bash
# LLM
OLLAMA_MODEL=llama3.2:1b
LLM_TIMEOUT=120
OLLAMA_HOST=http://localhost:11434

# STT
WHISPER_MODEL=base
WHISPER_LANGUAGE=fr
AUDIO_MAX_SIZE_MB=10

# TTS
TTS_ENGINE=pyttsx3
TTS_LANGUAGE=fr
TTS_RATE=150

# Telegram (optionnel — laisser vide pour désactiver)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Watchdog (optionnel)
WATCHDOG_ENABLED=false

# API
NERON_API_KEY=changez_moi
LOG_LEVEL=INFO
```

### Choisir le bon modèle LLM

|Modèle       |Latence CPU|Qualité français|RAM |
|-------------|-----------|----------------|----|
|`llama3.2:1b`|~38s       |⚠️ faible        |2 GB|
|`llama3.2:3b`|~86s       |✅ bonne         |4 GB|

```bash
# Changer le modèle interactivement
make ollama
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
make test
# ou
pytest neron_core -v
# 68+ tests passent
```

|Fichier de test        |Tests |Couvre                            |
|-----------------------|------|----------------------------------|
|`test_core_response.py`|8     |CoreResponse, timestamps, metadata|
|`test_orchestrator.py` |7     |IntentRouter, enum, valeurs       |
|`test_router.py`       |12    |Classification intents            |
|`test_stt_agent.py`    |11    |STTAgent, formats, erreurs        |
|`test_tts_agent.py`    |9     |TTSAgent, synthèse, erreurs       |
|`test_time_provider.py`|15    |TimeProvider, formats             |
|`test_web_agent.py`    |6     |WebAgent, erreurs                 |
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


> Sur GPU, llama3.2:3b descend à ~2s.

-----

## 🛠️ Maintenance

### Logs

```bash
make logs
journalctl -u neron -f
```

### Sauvegarde

```bash
make backup
make restore
```

### Mise à jour

```bash
make update
```

-----

## 🐛 Dépannage

### Néron ne démarre pas

```bash
make logs
make env   # vérifier la configuration
```

### LLM trop lent

Modifier `OLLAMA_MODEL=llama3.2:1b` dans `.env` puis `make restart`.

### STT transcription incorrecte

Vérifier `WHISPER_LANGUAGE=fr` dans `.env`. Essayer `WHISPER_MODEL=small`.

### Ollama non accessible

```bash
systemctl status ollama
ollama serve &
```

-----

## 🗺️ Roadmap

- [x] Pipeline texte (v1.1.0)
- [x] Mémoire persistante SQLite (v1.2.0)
- [x] Intent router + WebAgent (v1.3.0)
- [x] TimeProvider, métriques Prometheus (v1.4.0)
- [x] Pipeline audio STT faster-whisper (v1.5.0)
- [x] Pipeline vocal complet STT + TTS (v1.6.0)
- [x] Bots Telegram bidirectionnels (v1.14.0)
- [x] Watchdog supervision auto (v1.8.0)
- [x] **Architecture native sans Docker** (v2.0.0)
- [ ] Intégration Home Assistant (v2.1.x)
- [ ] Streaming LLM natif
- [ ] Support GPU
- [ ] RAG — Retrieval-Augmented Generation

-----

## 📚 Documentation

- [QUICKSTART](QUICKSTART.md) — Démarrage rapide
- [CHANGELOG](CHANGELOG.md) — Historique des versions
- [CONTRIBUTING](CONTRIBUTING.md) — Guide de contribution

-----

## 📄 Licence

Ce projet est sous licence MIT.

-----

## 🙏 Remerciements

- [Ollama](https://ollama.com/) — Moteur LLM local
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — STT optimisé CPU
- [FastAPI](https://fastapi.tiangolo.com/) — Framework web
- [pyttsx3](https://pyttsx3.readthedocs.io/) — TTS offline
- [python-telegram-bot](https://python-telegram-bot.org/) — Intégration Telegram

-----

**Fait avec ❤️ — Néron AI v2.0.0**