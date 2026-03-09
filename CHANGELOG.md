# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.2.2/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

-----

## [À venir]

#### En cours

- **ha_agent.py** — contrôle Home Assistant

#### Planifié

- **ha_agent.py** — contrôle Home Assistant complet (v2.1.x)
- **Prometheus** — agent séparé pour scraping /metrics
- **Grafana** — dashboards et alerting
- **Streaming LLM** — support streaming natif
- **Multi-utilisateurs** — support plusieurs utilisateurs Telegram
- **Interface mobile** — application native
- **Plugins** — architecture extensible
- **neron_hud** — remise en service interface HUD (v2.x)

-----

## [v2.0.0] - 2026-03-09

### ⚡ Migration monolithe — Architecture native sans Docker

Refonte complète de l’architecture : abandon de l’orchestration Docker multi-conteneurs
au profit d’un processus Python unique avec agents intégrés.

### Ajouts

- **Architecture native** — 1 seul processus Python, 0 Docker requis
- **Service systemd** — `neron.service` avec restart automatique et démarrage au boot
- **Makefile complet** — 15 commandes : `install`, `start`, `stop`, `restart`, `status`, `logs`, `update`, `clean`, `backup`, `restore`, `test`, `ollama`, `telegram`, `env`, `version`
- **install.sh** — bootstrap one-liner `curl -fsSL .../install.sh | bash`
  - Vérification OS Ubuntu/Debian
  - Vérification RAM (min 2GB) et disque (min 10GB)
  - Installation Ollama si absent
  - Clone ou mise à jour du dépôt
  - Création `.env` depuis `.env.example`
  - Téléchargement modèle Ollama
- **`make ollama`** — gestion interactive du modèle (liste installés + recommandés, pull sécurisé, mise à jour `.env`)
- **`make telegram`** — configuration interactive bots Telegram (token, chat_id auto via getUpdates)
- **Bot Telegram optionnel** — Néron démarre même sans token configuré
- **Watchdog optionnel** — activé via `WATCHDOG_ENABLED=true` dans `.env`
- **Page web** — site de présentation du projet (`index.html`)

### Suppressions

- **Docker** — suppression complète de l’orchestration Docker
- **neron_system.py** — remplacé par `neron_core/app.py` v2
- **start_neron.sh** — remplacé par `Makefile`
- **modules/neron_telegram** — intégré dans `neron_core/agents/telegram_agent.py`
- **modules/neron_watchdog** — intégré dans `neron_core/agents/watchdog_agent.py`
- **docker-compose.yaml** — obsolète

### Corrections

- **Chemins absolus** — suppression complète de tous les `/mnt/usb-storage/Neron_AI`
  - `memory_agent.py`, `stt_agent.py`, `watchdog_agent.py` — chemins relatifs via `__file__`
  - `neron.service` — placeholders `__NERON_DIR__` et `__NERON_USER__` générés par `make install`
  - `Makefile` — `BASE_DIR` dynamique via `$(shell dirname $(realpath ...))`
  - `install.sh` — `INSTALL_DIR` configurable via `NERON_DIR`
- **`neron_core/app.py`** — commentaire `v1.4.0` corrigé en `v2.0.0`
- **`neron_core/app.py`** — `/input/voice` déplacée avant `if __name__`
- **`neron_core/app.py`** — `import json` supprimé dans `text_input_stream` (doublon)
- **`neron_core/app.py`** — `StreamingResponse` importé en haut du fichier
- **`python3.12-venv`** → `python3-venv` générique (compatible Ubuntu 22.04+)
- **`mkdir -p data/`** — ajouté dans `make install` (fix SQLite `unable to open database`)

### Améliorations

- **VERSION** — `1.4.0` → `2.0.0` dans `app.py`
- **`neron.service`** — `StartLimitIntervalSec` déplacé dans `[Unit]` (fix warning systemd)
- **`.env.example`** — mis à jour pour v2 (suppression variables Docker, ajout `WATCHDOG_ENABLED`)

-----

## [v1.17.0] - 2026-03-01

### Ajouts

- **neron_hud** — nouveau module interface HUD style JARVIS (port 8085)
  - Dashboard React/TypeScript avec CSS vanilla (zéro Tailwind)
  - Score système et liste services en temps réel (polling watchdog)
  - Animation centrale ArcReactor avec anneaux rotatifs (requestAnimationFrame)
  - Interface chat textuel connectée à neron_core
  - Reconnaissance vocale via MediaRecorder API → STT → neron_core
  - Panneau anomalies depuis watchdog
  - Horloge temps réel
  - Build Docker multi-stage Node 20
- **cloudflared** — tunnel HTTPS gratuit via trycloudflare.com
  - Service systemd `cloudflared-hud` avec restart automatique
  - Service systemd `cloudflared-hud-notify` — envoi URL Telegram au démarrage
- **neron_telegram** — commande `/url` pour récupérer URL HUD Cloudflare

### Corrections

- Fix `/api/system/metrics` — services est un objet et non un tableau
- Fix endpoint STT `/speech` → `/transcribe`
- Fix `NERON_API_KEY` manquant dans environment neron_hud
- Fix horloge HUD figée — remplacée par setInterval React

-----

## [v1.16.0] - 2026-02-27

### Ajouts

- Volumes persistants USB pour watchdog (JSONL), memory (SQLite) et ollama (modèles)
- Endpoint API watchdog `/logs/<service>` via socket Docker unix
- Endpoint API watchdog `/history/<service>` depuis mémoire JSONL
- Commandes Telegram `/logs <service>` et `/history <service>`
- Menu /start mis à jour avec les nouvelles commandes

### Corrections

- Fix schéma memory.db : colonne `timestamp` manquante causait 34 crashs en boucle
- Fix endpoints /logs et /history placés après `asyncio.run()` (jamais exécutés)
- Fix `HTTPException` non importé dans watchdog
- Fix doublon `volumes:` et `group_add` dans docker-compose.yaml
- Fix token Telegram exposé dans les logs (rotation recommandée)

### Améliorations

- Hot-reload app.py sans rebuild pour neron_telegram, neron_watchdog, neron_core
- Migration `docker cp` pour forcer la mise à jour du fichier dans le conteneur
- Toutes les modifications de fichiers via Python (abandon de sed)

-----

## [v1.15.0] - 2026-02-27

### Ajouts

- **Rapport quotidien** — score de santé /100 intégré
- **Rapport quotidien** — tendance hebdomadaire (amélioration/dégradation/stable)
- **Pause automatique rebuild** — watchdog détecte les rebuilds Docker et se met en pause
  - Détection via events Docker (image build + container destroy)
  - Reprise automatique après 60s
  - Notification Telegram pause/reprise
  - Dies ignorés pendant rebuild (pas de faux restarts)

-----

## [v1.14.0] - 2026-02-26

### Ajouts

- **neron_telegram** — module Telegram dédié bidirectionnel (port 8010)
  - Bot bidirectionnel — commandes depuis Telegram
  - `/start`, `/status`, `/stats`, `/rapport`, `/score`, `/anomalies`, `/restart <service>`, `/pause`, `/resume`
  - Whitelist chat_id — sécurité
  - Endpoint `/notify` — réception notifications des autres modules
  - Messages texte → neron_core avec API Key
- **API HTTP watchdog** — endpoints REST sur port 8003
  - `/status`, `/score`, `/anomalies`, `/docker-stats`, `/rapport`, `/pause`, `/resume`, `/restart/<service>`
- **Refactoring notifier** — neron_watchdog délègue à neron_telegram via `/notify`

-----

## [v1.13.1] - 2026-02-26

### Ajouts

- **Authentification API Key** — protection endpoint `/input/text` (401/403)
- **API Key propagée** — neron_web_voice transmet la clé à neron_core
- **Stats Docker par conteneur** — CPU/RAM/réseau toutes les 5min
- **Stats Docker dans rapport** — section conteneurs dans le rapport 19h
- **Détecteurs anomalies améliorés** — corrélation CPU/RAM et memory leak basés sur vraies stats

### Améliorations

- **env_file** — docker-compose pointe vers `/opt/Neron_AI/.env`
- **Seuils CPU** — alerte warn 95%, critique 100% (adapté LLM)

-----

## [v1.13.0] - 2026-02-26

### Ajouts

- **Authentification API Key** — header `X-API-Key` sur neron_core

-----

## [v1.12.0] - 2026-02-26

### Ajouts

- **Stats Docker** — collecteur CPU/RAM/réseau par conteneur
- **Alertes conteneur** — seuils CPU/RAM par conteneur
- **Intégration rapport** — stats Docker dans rapport quotidien

-----

## [v1.11.0] - 2026-02-26

### Ajouts

- **Détection anomalies** — 12 patterns détectés automatiquement
  - Crash récurrent à la même heure
  - Dégradation progressive
  - Cascade de crashs
  - Crash après redémarrage
  - Fréquence croissante
  - Corrélation CPU/RAM
  - Memory leak pattern
  - Dépendance en cascade
  - Jour de la semaine
  - Heure de pointe
  - Score de santé global
  - Tendance hebdomadaire

-----

## [v1.10.0] - 2026-02-26

### Ajouts

- **Rapport quotidien 19h** — uptime%, crashs, services instables
- **Envoi Telegram** — rapport automatique chaque soir

-----

## [v1.9.0] - 2026-02-26

### Ajouts

- **Mémoire stratégique JSONL** — journal crash/restart/recovery/instabilité
- **Rétention 30 jours** — purge automatique
- **Stats système** — CPU/RAM global enregistré

-----

## [v1.8.2] - 2026-02-26

### Corrections

- **Verrou anti-restart concurrent** — asyncio.Lock par service
- **Filtre événements anciens** — ignore events Docker avant démarrage watchdog

-----

## [v1.8.1] - 2026-02-26

### Améliorations

- **Renommage** — neron_control → neron_watchdog

-----

## [v1.8.0] - 2026-02-26

### Ajouts

- **Auto-restart autonome** — 3 tentatives silencieuses avec escalade
- **Détection instabilité** — alerte après 3 crashs en 10min
- **Docker Events** — surveillance temps réel

-----

## [v1.7.4] - 2026-02-26

### Ajouts

- Module `neron_control` : agent de gardiennage autonome
  - Health checks de 8 services en parallèle
  - Notifications Telegram enrichies (DOWN / UP / Performance dégradée / Micro-coupure)
  - Watchdog Docker Events : détection instantanée des crashes via socket Unix
  - Retry intelligent : retry 10s avant alerte, micro-coupure loggée et notifiée
  - Collecteur métriques système via `psutil` : CPU, RAM, disques avec seuils configurables
  - Historique SQLite : uptime, incidents, temps de réponse
  - Configuration JSON par service (`neron.json`)
  - Support `ssl_verify`, `health_path`, `host` par service
  - Montage socket Docker `/var/run/docker.sock` pour events temps réel

### Corrections

- Fix encodage caractères typographiques dans tous les fichiers Python
- Fix signature `NeronServiceChecker.__init__()`
- Fix URLs services Docker
- Fix réseau `neron_internal` manquant pour `neron_control`
- Fix certificats SSL `neron_web_voice`
- Fix JSON parsing `neron.json`
- Fix `neron_web_voice` HTTPS — `ssl_verify: false`
- Fix permissions socket Docker — `group_add` avec GID docker

### Suppressions

- Service `neron_web` (Gradio) — remplacé par `neron_web_voice`

-----

## [v1.7.0] - 2026-02-23

### Ajouts

- Service `neron_web_voice` v1.0.0 : interface vocale web (HTML/CSS/JS + Express)
- Pipeline vocal complet côté client : microphone → STT → LLM → TTS navigateur
- Serveur Express avec support HTTPS via certificats montés en volume Docker
- Proxy `/api/stt` et `/api/core`
- Route `/api/config` et `/api/health`
- Interface dark violet animée : orbe, waveform 15 barres, 4 états
- TTS via Web Speech Synthesis API (voix fr-FR, déverrouillage contexte audio Safari iOS)
- Compatible Safari iOS

### Corrections

- Route STT corrigée : `/speech` → `/transcribe`
- Mixed content HTTPS→HTTP résolu via proxy Express
- Problème multipart résolu
- Déverrouillage TTS Safari iOS au moment du tap utilisateur

-----

## [v1.6.0] - 2026-02-22

### Ajouts

- Service `neron_tts` v1.0.0 : synthèse vocale via pyttsx3
- `engine.py` : adapter pattern TTSEngine / Pyttsx3Engine (extensible vers Coqui, edge-tts)
- `tts_agent.py` : client HTTP vers neron_tts:8003
- Endpoint `POST /input/voice` : pipeline vocal complet audio → STT → LLM → TTS → audio WAV
- Headers de réponse : `X-Transcription`, `X-Response-Text`, `X-Intent`, `X-STT-Latency-Ms`, `X-TTS-Latency-Ms`
- 9 tests tts_agent

### Corrections

- `global tts_agent` manquant dans lifespan neron_core
- Guillemets typographiques → droits dans start_neron.sh

### Tests

- 68 tests passent (59 → 68)

-----

## [v1.5.0] - 2026-02-21

### Ajouts

- Service `neron_stt` v1.1.0 : transcription audio via faster-whisper int8
- `stt_agent.py` : client HTTP vers neron_stt:8001
- Endpoint `POST /input/audio` : audio → STT → pipeline texte → CoreResponse
- Champ `transcription` dans CoreResponse
- Métadonnées STT dans `metadata.stt`
- 11 tests stt_agent

### Optimisations

- openai-whisper → faster-whisper 1.0.3 (int8, CPU)
- STT latence : 24s → 7.8s (-68%)
- `WHISPER_LANGUAGE=fr` forcé
- Limite audio `AUDIO_MAX_SIZE_MB=10`
- Warmup au startup
- Modèle Whisper embarqué dans l’image Docker

### Tests

- 59 tests passent (48 → 59)

-----

## [v1.4.1] - 2026-02-21

### Améliorations

- **Néron Core** : passage à `python:3.11-slim` + multi-stage build — 14.6GB → 336MB
- **Néron LLM** : passage à `python:3.11-slim` — 266MB → 64MB
- **Néron Memory** : slim base, pip install sans cache
- **Néron Web** : base Python slim + pip no-cache

-----

## [v1.4.0] - 2026-02-20

### Ajouts

- **Isolation réseau Docker** — réseau `neron_internal` (bridge, internal: true)
- **CoreResponse enrichie** — champs `agent`, `timestamp`, `execution_time_ms`, `model`, `error`
- **Observabilité `/metrics`** — `neron_uptime_seconds`, `neron_requests_total`, `neron_requests_in_flight`, `neron_execution_time_avg_ms`, `neron_llm_calls_by_model`
- **VERSION** — constante dans app.py
- 8 nouveaux tests `test_core_response.py`

### Tests

- 48 tests passent (40 → 48)

-----

## [v1.3.3] - 2026-02-19

### Ajouts

- Handler `_handle_time_query` dans app.py : répond sans passer par le LLM
- `TimeProvider` instancié au startup
- Réponse en français avec jours et mois localisés

### Corrections

- `llm_agent.py` : lit `OLLAMA_MODEL` depuis `.env`
- Dockerfile : ajout `COPY neron_time/` manquant

-----

## [v1.3.2] - 2026-02-19

### Ajouts

- `neron_time/time_provider.py` : fournit heure, date, iso, timestamp
- Fuseau horaire configurable via `zoneinfo` (stdlib Python 3.9+)
- `Intent.TIME_QUERY` dans `intent_router.py`
- 15 tests pytest TimeProvider + 3 tests TIME_QUERY

### Tests

- 40 tests passent

-----

## [v1.3.1] - 2026-02-19

### Corrections

- `web_agent.py` : capture séparée de chaque type d’erreur HTTP
- `llm_agent.py` : timeout granulaire via `httpx.Timeout`
- Fallback propre vers conversation si WebAgent indisponible
- SearXNG : port 8888 supprimé (réseau interne Docker uniquement)
- Dockerfile neron_core : user non-root `neron`
- JSON logging structuré sur tous les composants
- Endpoint `/metrics` Prometheus sur neron_core

### Tests

- 22 tests pytest passent

-----

## [v1.3.0] - 2026-02-19

### Ajouts

- Neron Core devient un orchestrateur multi-agents
- `IntentRouter` : classification rules-based + LLM fallback
- `BaseAgent` : classe abstraite commune, AgentResult standardisé
- `LLMAgent`, `WebAgent` (SearXNG self-hosted)
- Intents : `CONVERSATION`, `WEB_SEARCH`, `TIME_QUERY`, `HA_ACTION`
- Nouveau service `neron_searxng` dans docker-compose

-----

## [v1.2.2] - 2025-02-15

### Version Initiale de Production

Première version stable avec architecture microservices Docker.

- **neron_core** v0.2.0 — orchestrateur FastAPI
- **neron_llm** v1.2.2 — wrapper Ollama, 40+ tests, coverage > 95%
- **neron_stt** v0.1.0 — transcription Whisper
- **neron_memory** v0.2.0 — SQLite persistant
- **neron_web** v0.1.0 — interface Gradio 4.16
- **neron_ollama** — Llama 3.2 / Mistral / Phi-3 / Gemma

-----

## [v0.2.0] - 2025-02-10

### Beta

- neron_core et neron_memory
- Intégration basique Ollama
- Interface web Gradio basique

-----

## [v0.1.0] - 2025-02-01

### Alpha

- Structure de projet initiale
- Docker Compose basique
- Modules neron_core et neron_stt en développement

-----

## Versioning

- **MAJOR** (X.0.0) : Changements incompatibles avec l’API
- **MINOR** (0.X.0) : Nouvelles fonctionnalités rétrocompatibles
- **PATCH** (0.0.X) : Corrections de bugs rétrocompatibles