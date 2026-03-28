Complete project analysis

Read [](file:///mnt/usb-storage/neron/server/README.md#1-1), lines 1 to 150

Read [](file:///mnt/usb-storage/neron/server/requirements.txt)

Read [](file:///mnt/usb-storage/neron/server/core/app.py#1-1), lines 1 to 100

Read [](file:///mnt/usb-storage/neron/server/neron.yaml.example)

Read [](file:///mnt/usb-storage/neron/server/core/agents)

Read [](file:///mnt/usb-storage/neron/server/core/app.py#100-100), lines 100 to 300

Read [](file:///mnt/usb-storage/neron/server/core/agents/base_agent.py#1-1), lines 1 to 50

Read [](file:///mnt/usb-storage/neron/server/core/modules/agent_router.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/modules)

Read [](file:///mnt/usb-storage/neron/server/core/orchestrator)

Read [](file:///mnt/usb-storage/neron/server/core/orchestrator/intent_router.py)

Read [](file:///mnt/usb-storage/neron/server/core/agents/llm_agent.py#1-1), lines 1 to 60

Read [](file:///mnt/usb-storage/neron/server/core/agents/stt_agent.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/agents/tts_agent.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/agents/web_agent.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/agents/memory_agent.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/agents/watchdog_agent.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/agents/ha_agent.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/agents/code_agent.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/agents/telegram_agent.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/modules/gateway.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/modules/sessions.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/modules/skills.py#1-1), lines 1 to 80

Read [](file:///mnt/usb-storage/neron/server/core/modules/world_model.py)

Read [](file:///mnt/usb-storage/neron/server/core/modules/scheduler.py#1-1), lines 1 to 100

Read [](file:///mnt/usb-storage/neron/server/core/neron_time/time_provider.py)

Read [](file:///mnt/usb-storage/neron/server/core/config.py#1-1), lines 1 to 100

Read [](file:///mnt/usb-storage/neron/server/core/constants.py)

Read [](file:///mnt/usb-storage/neron/server/core/app.py#300-300), lines 300 to 500

Read [](file:///mnt/usb-storage/neron/server/CONTRIBUTING.md#1-1), lines 1 to 100

Created memory file [](file:///home/eleazar/.vscode-server/data/User/workspaceStorage/ddfa1e5cb4935db115540b521738ed2e/GitHub.copilot-chat/memory-tool/memories/NzMzMjIxN2YtNmJmNC00YjBlLWJhMjMtNDc4MDg2NGJlMjk2/neron_analysis.md)

Read [](file:///home/eleazar/.vscode-server/data/User/workspaceStorage/ddfa1e5cb4935db115540b521738ed2e/GitHub.copilot-chat/chat-session-resources/7332217f-6bf4-4b0e-ba23-4780864be296/call_98934522__vscode-1774650950768/content.txt)

## Analyse Complète du Projet Neron AI

Voici une analyse détaillée du projet Neron AI basée sur l'exploration approfondie du code source :

### **Vue d'ensemble et Architecture**

**Neron AI** (version 2.2.0) est un **assistant IA local modulaire open-source** qui fonctionne 100% localement sans cloud ni Docker dans un seul processus Python. Tous les composants coexistent dans une boucle d'événements asyncio sur le port 8000, avec des services auxiliaires optionnels (SearXNG sur 8080, Ollama sur 11434, passerelle WebSocket sur 18789).

**Style d'architecture** : Patterns microservices (agents, modules, orchestrateurs) empaquetés en monolithe. Inspiré d'OpenClaw (boucles LLM, registres d'outils, gestion de sessions).

### **Composants Clés**

#### **Serveur FastAPI** (app.py)
- Orchestrateur central sur port 8000
- Gestion du cycle de vie (démarrage/arrêt de tous les agents, services, planificateurs)
- API REST avec métriques (Prometheus) et authentification API-Key optionnelle
- Trois pipelines d'entrée : `POST /input/text`, `POST /input/audio`, `POST /input/voice`

#### **IntentRouter** (`orchestrator/intent_router.py`)
Route les requêtes utilisateur via classification par mots-clés :
- **time_query** → TimeProvider (réponse immédiate)
- **web_search** → WebAgent (SearXNG)
- **ha_action** → HAAgent (Home Assistant)
- **code** → CodeAgent (multi-étapes LLM + outils)
- **personality_feedback** → Module personnalité
- **conversation** → LLMAgent (fallback)

### **Tous les Agents et Leurs Fonctionnalités**

| Agent | Rôle | Fonctionnalités Clés |
|-------|------|---------------------|
| **llm_agent** | Conversation/LLM | Intégration Ollama, personnalité dynamique optionnelle, streaming des réponses |
| **stt_agent** | Speech-to-Text | faster-whisper (modèle base, CPU int8), supporte WAV/MP3/M4A/OGG/FLAC/WEBM, français par défaut, max 10MB |
| **tts_agent** | Text-to-Speech | espeak+ffmpeg, sortie MP3, limite 1000 caractères, français par défaut |
| **memory_agent** | Stockage Conversations | SQLite direct (pas HTTP), rétention auto (30 jours), rotation ~10k lignes |
| **web_agent** | Recherche Web | Instance SearXNG locale, 5 résultats max, langue française, recherche sécurisée désactivée |
| **ha_agent** | Home Assistant | API REST, détection domaine (lumières/volets/climat/etc), correspondance floue d'entités, timeout 10s |
| **code_agent** | Génération/Révision Code | Actions : generate/improve/analyze/read/self_review/rollback, boucle LLM, sandbox (10s), système de sauvegarde |
| **telegram_agent** | Chat Bot | Optionnel, bidirectionnel, IDs chat autorisés, commandes /help /status /health |
| **watchdog_agent** | Surveillance Système | Alertes CPU/RAM/disque/température, détection anomalies, redémarrage auto, notifications Telegram, scoring santé |
| **system_agent** | Infos Système | Requêtes système basiques |
| **base_agent** | Classe Base | Logging ColorFormatter, dataclass AgentResult, utilitaires timer, helpers succès/échec |

### **Modules et Leurs Rôles**

| Module | Rôle |
|--------|------|
| **gateway.py** | Serveur WebSocket (ws://0.0.0.0:18789), JSON-RPC 2.0, auth token, max 10MB par message |
| **sessions.py** | Persistance sessions JSONL, écriture en append, estimation tokens (~8000 max), pruning overflow |
| **skills.py** | Système plugins, chargement depuis SKILL_DIR, triggers, registre outils, handlers async+sync |
| **world_model.py** | État centralisé (agents/modules/système/temps), singleton partagé, tracking timestamps |
| **scheduler.py** | Wrapper APScheduler, jobs cron : revue nocturne auto, nettoyage mémoire, rapports quotidiens |
| **agent_router.py** | Boucles LLM, dispatch outils, gestion sessions, injection skills |
| **neron_time** | Classe TimeProvider, timezone localisée (Europe/Paris), formats multiples |
| **personality** | Humeur/énergie/ton dynamique optionnel, build_system_prompt(), dégradation gracieuse |

### **Système de Configuration**

**Hiérarchie des sources** : neron.yaml (priorité) → variables d'environnement (fallback)

**Paramètres clés** :
```yaml
llm:        host, model (llama3.2:1b), max_tokens (2048), temperature (0.7), timeout (300s)
stt:        model (base), language (fr), max_size_mb (10), download_root
tts:        engine (pyttsx3), language (fr), rate (150), max_chars (1000)
memory:     db_path (data/memory.db), retention_days (30)
searxng:    url (localhost:8080), timeout (10s), max_results (5)
telegram:   bot_token, chat_id, enabled (false par défaut)
watchdog:   enabled, bot_token, thresholds (CPU 95%, RAM 85%, DISK 90%, TEMP 75°C)
server:     host (0.0.0.0), port (8000)
neron:      api_key, log_level, system_prompt
```

### **Technologies et Dépendances**

**Cœur** : FastAPI + UVicorn, asyncio, SQLite, httpx

**ML/Audio** : Ollama, faster-whisper, pyttsx3 + espeak + ffmpeg

**Intégrations** : SearXNG, Home Assistant, Telegram

**Infrastructure** : Prometheus, APScheduler, python-multipart, PyYAML, psutil

### **Flux d'Interaction des Composants**

```
Requête Utilisateur (texte/audio/voix)
    ↓
Endpoint FastAPI (/input/*)
    ↓
IntentRouter.route() [matching mots-clés → Enum Intent]
    ↓
Handler spécifique :
  ├─ TIME_QUERY       → TimeProvider (instantané)
  ├─ WEB_SEARCH       → WebAgent + SearXNG
  ├─ HA_ACTION        → HAAgent + API Home Assistant
  ├─ CODE             → CodeAgent (boucle LLM + outils)
  ├─ CONVERSATION     → LLMAgent (Ollama)
  └─ PERSONALITY_FBK  → Module personnalité
    ↓
[Optionnel] STT si entrée audio
[Toujours] MemoryAgent stocke résultat + métadonnées
[Optionnel] TTS si endpoint voice
    ↓
CoreResponse JSON ou stream WAV
```

### **Patterns et Décisions de Design Notables**

1. **Monolithe monoprocès avec concurrence async**
2. **Dégradation gracieuse** (composants optionnels)
3. **Routing basé sur intentions** (classification mots-clés)
4. **Pattern registre d'outils** (inspiré OpenClaw)
5. **Stratégie double-bot Telegram**
6. **Système auto-sauvegarde & rollback**
7. **Opérations planifiées** (revues nocturnes, nettoyages)
8. **Modèle monde centralisé** (vérité unique)
9. **Historique sessions append-only**
10. **Exécution code en sandbox**

### **API REST**

**Système** : `GET /`, `/health`, `/status`, `/metrics`

**Personnalité** : `GET /personality/state`, `/history`, `POST /reset`

**Entrées** : `POST /input/text`, `/audio`, `/voice`, `/stream`

**Home Assistant** : `POST /ha/reload`

### **Observations Clés**

✅ **Forces** : 100% local, simplicité déploiement, extensible, métriques riches, auto-observant, design français-first

⚠️ **Compromis** : Pas de scaling horizontal, boucle partagée, routing non-ML

📋 **Philosophie** : Monolithe-first, code direct préféré, fail-safe, ops-aware

Cette architecture positionne Neron AI comme un **assistant digital privacy-first, auto-contenu** optimisé pour l'usage personnel/domotique sur matériel contraint (Raspberry Pi, NAS, etc.).