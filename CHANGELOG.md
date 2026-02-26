# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.2.2/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

---

## [À venir]

#### En cours
- **Watchdog** — score santé + tendance hebdo intégrés dans rapport quotidien
- **Watchdog** — mode pause automatique pendant rebuild

#### Planifié
- **Watchdog** — endpoint HTTP pour consulter l'état
- **neron_telegram** — port 8010, remplacement notifier dans tous les modules
- **ha_agent.py** — contrôle Home Assistant (v1.4.x)
- **Prometheus** — agent séparé pour scraping /metrics
- **Grafana** — dashboards et alerting
- **Redis Event Bus** — remplacement REST interne
- **Streaming LLM** — support streaming pour les réponses LLM
- **Multi-utilisateurs** — support plusieurs utilisateurs
- **Interface mobile** — application native
- **Plugins** — architecture extensible

-----

## [v1.14.0] - 2026-02-26

### ✨ Nouveautés
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

### ✨ Nouveautés
- **Authentification API Key** — protection endpoint `/input/text` (401/403)
- **API Key propagée** — neron_web_voice transmet la clé à neron_core
- **Stats Docker par conteneur** — CPU/RAM/réseau toutes les 5min
- **Stats Docker dans rapport** — section conteneurs dans le rapport 19h
- **Détecteurs anomalies améliorés** — corrélation CPU/RAM et memory leak basés sur vraies stats

### 🔧 Améliorations
- **env_file** — docker-compose pointe vers `/opt/Neron_AI/.env`
- **Seuils CPU** — alerte warn 95%, critique 100% (adapté LLM)

---

## [v1.13.0] - 2026-02-26

### ✨ Nouveautés
- **Authentification API Key** — header `X-API-Key` sur neron_core

---

## [v1.12.0] - 2026-02-26

### ✨ Nouveautés
- **Stats Docker** — collecteur CPU/RAM/réseau par conteneur
- **Alertes conteneur** — seuils CPU/RAM par conteneur
- **Intégration rapport** — stats Docker dans rapport quotidien

---

## [v1.11.0] - 2026-02-26

### ✨ Nouveautés
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

---

## [v1.10.0] - 2026-02-26

### ✨ Nouveautés
- **Rapport quotidien 19h** — uptime%, crashs, services instables
- **Envoi Telegram** — rapport automatique chaque soir

---

## [v1.9.0] - 2026-02-26

### ✨ Nouveautés
- **Mémoire stratégique JSONL** — journal crash/restart/recovery/instabilité
- **Rétention 30 jours** — purge automatique
- **Stats système** — CPU/RAM global enregistré

---

## [v1.8.2] - 2026-02-26

### 🔧 Corrections
- **Verrou anti-restart concurrent** — asyncio.Lock par service
- **Filtre événements anciens** — ignore events Docker avant démarrage watchdog

---

## [v1.8.1] - 2026-02-26

### 🔧 Refactoring
- **Renommage** — neron_control → neron_watchdog

---

## [v1.8.0] - 2026-02-26

### ✨ Nouveautés
- **Auto-restart autonome** — 3 tentatives silencieuses avec escalade
- **Détection instabilité** — alerte après 3 crashs en 10min
- **Docker Events** — surveillance temps réel

---

## [1.7.4] - 2026-02-26

### Ajouts
- Module `neron_control` : agent de gardiennage autonome
  - Health checks de 8 services en parallèle (Core, STT, Memory, TTS, LLM, Ollama, SearXNG, Web Voice)
  - Notifications Telegram enrichies (DOWN / UP / Performance dégradée / Micro-coupure)
  - Watchdog Docker Events : détection instantanée des crashes via socket Unix
  - Retry intelligent Option 3 : retry 10s avant alerte, micro-coupure loggée et notifiée
  - Collecteur métriques système via `psutil` : CPU, RAM, disques avec seuils configurables
  - Historique SQLite : uptime, incidents, temps de réponse
  - Configuration JSON par service (`neron.json`) — ajout d'un service sans rebuild
  - Support `ssl_verify`, `health_path`, `host` par service
  - Montage socket Docker `/var/run/docker.sock` pour events temps réel
  - Montage des points de montage `/mnt/Data`, `/mnt/usb-storage`, `/mnt/Backup`

### Corrections
- Fix encodage caractères typographiques (guillemets UTF-8) dans tous les fichiers Python
- Fix signature `NeronServiceChecker.__init__()` — ajout `health_path`, `ssl_verify`
- Fix URLs services : chaque service utilise son propre `host` Docker
- Fix réseau `neron_internal` manquant pour `neron_control`
- Fix certificats SSL `neron_web_voice` — dossiers vides remplacés par vrais certificats
- Fix JSON parsing `neron.json` — caractères typographiques supprimés
- Fix `neron_web_voice` HTTPS — `ssl_verify: false` + scheme `https://`
- Fix permissions socket Docker — `group_add` avec GID du groupe docker

### Suppressions
- Service `neron_web` (Gradio) retiré — `neron_web_voice` est la seule interface

### Architecture

```
neron_control/
├── app.py                    # Orchestrateur principal
├── src/
│   ├── checkers/neron.py     # Health checks services
│   ├── collectors/system.py  # Métriques CPU/RAM/disques
│   ├── watchers/docker_events.py  # Events Docker temps réel
│   ├── notifiers/telegram.py # Notifications Telegram
│   └── database/history.py  # Historique SQLite
└── config/neron.json         # Configuration services
```

### Seuils métriques par défaut
- CPU warn: 75% / critical: 90%
- RAM warn: 80% / critical: 95%
- Disque warn: 75% / critical: 90%

### Docker
- Volume `/var/run/docker.sock` monté en lecture seule
- Volumes `/mnt/Data`, `/mnt/usb-storage`, `/mnt/Backup` montés en lecture seule
- Réseaux : `Neron_Network` + `neron_internal`
- `group_add` avec GID docker pour accès socket

-----

## [1.7.0] - 2026-02-23

### Ajouts
- Service `neron_web_voice` v1.0.0 : interface vocale web (HTML/CSS/JS + Express)
- Pipeline vocal complet cote client : microphone -> STT -> LLM -> TTS navigateur
- Serveur Express avec support HTTPS via certificats montes en volume Docker
- Proxy `/api/stt` : relay multipart -> `neron_stt:8001/transcribe`
- Proxy `/api/core` : relay JSON -> `neron_core:8000/input/text`
- Route `/api/config` : lecture et mise a jour des URLs des services
- Route `/api/health` : statut du serveur
- Interface dark violet animee : orbe, waveform 15 barres, 4 etats (idle / listening / processing / speaking)
- TTS via Web Speech Synthesis API (voix fr-FR, deverrouillage contexte audio Safari iOS)
- Compatible Safari iOS : ES5, format audio mp4, installation certificat profil
- Configuration via `.env` : PORT, NERON_CORE_URL, NERON_STT_URL

### Architecture

Safari iOS / Navigateur
| HTTPS :8080
v
neron_web_voice (Express)
|               |
| HTTP :8001    | HTTP :8000
v               v
neron_stt        neron_core
(Whisper)        (LLM Ollama)


### Docker
- Dockerfile optimise : node:20-slim, npm ci --omit=dev, NODE_ENV=production
- Reseaux : Neron_Network + neron_internal
- Certificats HTTPS montes en volume (:ro)
- Port expose : 8080

### Corrections
- Route STT corrigee : /speech -> /transcribe
- Mixed content HTTPS->HTTP resolu via proxy Express
- Probleme multipart resolu : express.json() retire de /api/stt
- Exposition Docker neron_stt sur Neron_Network
- Deverrouillage TTS Safari iOS au moment du tap utilisateur

### Documentation
- README.md neron_web_voice : architecture, installation, endpoints, HTTPS iOS
- CHANGELOG.md neron_web_voice v1.0.0

-----

## [1.6.0] - 2026-02-22

### Ajouts
- Service `neron_tts` v1.0.0 : synthèse vocale via pyttsx3
- `engine.py` : adapter pattern TTSEngine / Pyttsx3Engine (extensible)
- `tts_agent.py` : client HTTP vers neron_tts:8003
- Endpoint `POST /input/voice` : pipeline vocal complet audio → STT → LLM → TTS → audio WAV
- 9 tests tts_agent

### Architecture
POST /input/voice
→ neron_stt (faster-whisper) → transcription
→ intent router → LLM / time / web
→ neron_tts (pyttsx3) → audio WAV
=======
- `engine.py` : adapter pattern TTSEngine / Pyttsx3Engine (extensible vers Coqui, edge-tts)
- `tts_agent.py` : client HTTP vers neron_tts:8003
- Endpoint `POST /input/voice` : pipeline vocal complet audio → STT → LLM → TTS → audio WAV
- Headers de réponse : `X-Transcription`, `X-Response-Text`, `X-Intent`, `X-STT-Latency-Ms`, `X-TTS-Latency-Ms`
- 9 tests tts_agent

### Architecture pipeline vocal
```
POST /input/voice
  → neron_stt (faster-whisper int8) → transcription
  → intent router → LLM / time_provider / web
  → neron_tts (pyttsx3) → audio WAV
```

### Corrections
- `global tts_agent` manquant dans lifespan neron_core
- Guillemets typographiques → droits dans start_neron.sh

### Documentation
- README.md mis à jour : architecture complète, services, API, performances
- QUICKSTART.md mis à jour : exemples /input/audio et /input/voice
- CHANGELOG.md complet v1.0.0 → v1.6.0
- start_neron.sh v1.6.0 : show_endpoints, git main

### Tests
- 68 tests passent (59 → 68)

---

## [1.5.0] - 2026-02-21

### Ajouts
- Service `neron_stt` v1.1.0 : transcription audio via faster-whisper int8
- `stt_agent.py` : client HTTP vers neron_stt:8001
- Endpoint `POST /input/audio` : audio → STT → pipeline texte → CoreResponse
- Champ `transcription` dans CoreResponse
- Métadonnées STT dans `metadata.stt` (language, stt_model, stt_latency_ms)
- 11 tests stt_agent

<<<<<<< HEAD
### Optimisations
=======
### Optimisations STT
>>>>>>> release/v1.6.0
- openai-whisper → faster-whisper 1.0.3 (int8, CPU)
- STT latence : 24s → 7.8s (-68%)
- `WHISPER_LANGUAGE=fr` forcé
- Limite audio `AUDIO_MAX_SIZE_MB=10`
<<<<<<< HEAD
- Warmup au startup
- Modèle Whisper embarqué dans l'image Docker (pas besoin internet au runtime)
=======
- Warmup au startup (transcription silence)
- Modèle Whisper embarqué dans l'image Docker (pas d'internet au runtime)
>>>>>>> release/v1.6.0

### Modèles LLM testés
- `llama3.2:1b` : 38s, qualité insuffisante
- `orca-mini` : 62s, mélange fr/en
- `llama3.2:3b` retenu : meilleure qualité français sur CPU-only

### Tests
- 59 tests passent (48 → 59)

-----

## [1.4.1] - 2026-02-21

### Optimisation des containers Docker

- **Néron Core** :
  ∙ Passage à `python:3.11-slim` + multi-stage build  
  ∙ Nettoyage des dépendances inutiles dans l’image finale  
  ∙ Taille passée de ~14,6 GB → ~336 MB (gain énorme de performance et I/O)  

- **Néron LLM** :
  ∙ Passage à `python:3.11-slim`  
  ∙ Nettoyage des dépendances et requirements rationalisés  
  ∙ Taille passée de ~266 MB → ~64 MB  

- **Néron Memory** :
  ∙ Slim base, pip install sans cache  
  ∙ Taille réduite significativement  

- **Néron Web** :
  ∙ Base Python slim + pip no-cache  
  ∙ Taille réduite au minimum nécessaire  

**Impact attendu** :  
- Réduction massive du temps de build et du temps de transfert des images  
- Moins d’espace disque utilisé → meilleure scalabilité pour futurs agents  
- Amélioration des performances I/O et du démarrage des services

-----

## [1.4.0] - 2026-02-20
Phase 1 — Isolation réseau Docker
Securite
	∙	Ajout réseau neron_internal (bridge, internal: true)
	∙	Suppression des ports exposés : neron_llm (5000), neron_ollama (11434), neron_memory (8002), neron_searxng (8080)
	∙	neron_core seul point d’entrée externe sur 0.0.0.0:8000
	∙	neron_web maintenu sur 7860 (accès direct navigateur)
	∙	neron_core et neron_web connectés aux deux réseaux (Neron_Network + neron_internal)
	∙	neron_stt commenté (non implémenté)
Phase 2 — Standardisation des réponses API
CoreResponse enrichie
	∙	Ajout champ agent : identifie quel agent a traité la requête
	∙	Ajout champ timestamp : UTC ISO 8601 systématique
	∙	Ajout champ execution_time_ms : temps total orchestration (distinct de latency_ms agent interne)
	∙	Ajout champ model : modèle LLM utilisé, null si TimeProvider
	∙	Ajout champ error : null si succès, message si échec
	∙	Constante VERSION dans app.py (plus de hardcoding)
	∙	Helper utc_now_iso() pour timestamp uniforme
Règle de nommage établie
	∙	latency_ms → métrique interne agent (AgentResult)
	∙	execution_time_ms → temps global orchestration (CoreResponse)
	∙	timestamp → toujours UTC ISO 8601 en exposition API
Tests
	∙	8 nouveaux tests test_core_response.py
	∙	Patch complet LLMAgent/WebAgent/Router/TimeProvider
	∙	Validation : tous les champs, timestamp UTC, execution_time_ms >= 0, error null
Phase 3 — Observabilité /metrics enrichie
Nouvelles métriques
	∙	neron_uptime_seconds : durée depuis le démarrage du service
	∙	neron_requests_total : compteur total de requêtes reçues
	∙	neron_requests_in_flight : requêtes en cours de traitement (gauge)
	∙	neron_execution_time_avg_ms : temps moyen d’orchestration global
	∙	neron_llm_calls_by_model : compteur d’appels LLM par modèle
Architecture métriques
	∙	record_request_start/end avec bloc finally (fiable même en cas d’erreur)
	∙	Latences stockées par agent (dict) au lieu de liste plate
	∙	/metrics passif, découplé — prêt pour scraping Prometheus externe
	∙	Prometheus sera ajouté comme agent séparé (non inclus dans cette version)
Validation
	∙	neron_agent_errors_total vérifié en production (test docker stop neron_llm)
	∙	p95/p99 reportés à l’intégration Prometheus (calcul natif côté Prometheus)
Tests
	∙	48 tests passent (40 existants + 8 nouveaux)

-----

## [1.3.3] - 2026-02-19

### Branchement TimeProvider dans le pipeline

#### Nouveautes

- Handler `_handle_time_query` dans app.py : repond sans passer par le LLM
- `TimeProvider` instancie au startup avec les autres agents
- Reponse en francais : "Il est jeudi 19 fevrier 2026 a 21h36."
- Jours et mois en francais via dictionnaires integres (sans dependance locale)
- `neron_time/` copie dans l'image Docker via Dockerfile

#### Corrections

- `llm_agent.py` : lit `OLLAMA_MODEL` depuis `.env` et le transmet a neron_llm
- Modele effectivement utilise retourne dans `metadata.model`
- Dockerfile : ajout `COPY neron_time/` manquant

-----

## [1.3.2] - 2026-02-19

### TimeProvider et intent TIME_QUERY

#### Nouveautes

- Ajout `neron_time/time_provider.py` : fournit heure, date, iso, timestamp
- Fuseau horaire configurable (defaut Europe/Paris) via `zoneinfo` (stdlib Python 3.9+)
- Methodes : `now()`, `iso()`, `human()`, `date()`, `time()`, `timestamp()`
- Ajout `Intent.TIME_QUERY` dans `intent_router.py`
- Patterns detectes : heure, date, quel jour, quel mois

#### Tests

- 15 tests pytest pour TimeProvider (15/15 PASS)
- 3 nouveaux tests TIME_QUERY dans test_router.py
- Total : 40 tests passes

-----

## [1.3.1] - 2026-02-19

### Corrections suite audit DevOps

#### Robustesse reseau

- `web_agent.py` : capture separee de chaque type d'erreur HTTP (TimeoutException, ConnectError, HTTPStatusError, RequestError)
- `llm_agent.py` : meme traitement, timeout granulaire via `httpx.Timeout`
- Fallback propre vers conversation si WebAgent indisponible

#### Architecture

- Router avec registre dynamique d'agents (`build_intent_registry`)
- Ajout de `meteo` sans accent dans les patterns du router (robustesse saisie utilisateur)
- Imports absolus partout, suppression des imports relatifs problematiques
- `__init__.py` vides pour eviter les conflits de chargement pytest

#### Securite

- SearXNG : port 8888 supprime du docker-compose (reseau interne Docker uniquement)
- Dockerfile neron_core : user non-root `neron`
- Healthcheck SearXNG corrige avec `wget`

#### Observabilite

- JSON logging structure sur tous les composants (agents, router, app)
- Endpoint `/metrics` Prometheus sur neron_core (compteurs intents, erreurs, latences)
- Mesure de latence sur chaque AgentResult

#### Tests

- 22 tests pytest passes : 7 orchestrator, 9 router, 6 web_agent
- `conftest.py` avec fixtures partagees
- `pytest.ini` configure avec asyncio_mode = auto

-----

## [1.3.0] - 2026-02-19

### Orchestrateur central - Neron Core

#### Nouveautes

- Neron Core devient un orchestrateur multi-agents
- `IntentRouter` : classification rules-based + LLM fallback
- `BaseAgent` : classe abstraite commune, AgentResult standardise
- `LLMAgent` : wrapper neron_llm en tant qu'agent
- `WebAgent` : recherche web via SearXNG self-hosted (meteo, actualites, recherches)
- Pipeline web : WebAgent -> SearXNG -> LLMAgent synthese -> reponse
- Nouveau service `neron_searxng` dans docker-compose

#### Intents supportes

- `CONVERSATION` : reponse LLM directe
- `WEB_SEARCH` : recherche SearXNG + synthese LLM (inclut meteo)
- `TIME_QUERY` : TimeProvider, sans LLM (ajoute en 1.3.2)
- `HA_ACTION` : reserve v1.4.0, slot en place dans le router

#### Structure ajoutee dans neron_core

```
agents/
  base_agent.py
  llm_agent.py
  web_agent.py
neron_time/
  time_provider.py
orchestrator/
  intent_router.py
tests/
  conftest.py
  test_orchestrator.py
  test_router.py
  test_time_provider.py
  test_web_agent.py
```

#### CoreResponse enrichie

```json
{
  "response": "...",
  "intent": "web_search",
  "confidence": "high",
  "metadata": {
    "model": "llama3.2:1b",
    "web_sources": ["url1", "url2"],
    "web_results_count": 12
  }
}
```

-----

## [1.2.2] - 2025-02-15

### Version Initiale de Production

Première version stable et complète de Néron AI avec architecture microservices.

#### Modules Core

**neron_core (v0.2.0)** - Orchestrateur central avec FastAPI, pipeline Texte -> LLM -> Mémoire

**neron_llm (v1.2.2)** - Wrapper HTTP autour d'Ollama, 40+ tests unitaires, coverage > 95%

**neron_stt (v0.1.0)** - Transcription audio Whisper, formats WAV/MP3/M4A/OGG

**neron_memory (v0.2.0)** - SQLite persistant, recherche full-text, endpoints store/retrieve/search/stats

**neron_web (v0.1.0)** - Interface Gradio 4.16

**neron_ollama** - Ollama officiel, modeles Llama 3.2 / Mistral / Phi-3 / Gemma

-----

## [0.2.0] - 2025-02-10

### Beta

- Version beta neron_core et neron_memory
- Integration basique Ollama
- Interface web Gradio basique

-----

## [0.1.0] - 2025-02-01

### Alpha

- Structure de projet initiale
- Docker Compose basique
- Modules neron_core et neron_stt en developpement

-----

## Versioning

- **MAJOR** (X.0.0) : Changements incompatibles avec l'API
- **MINOR** (0.X.0) : Nouvelles fonctionnalites retrocompatibles
- **PATCH** (0.0.X) : Corrections de bugs retrocompatibles
