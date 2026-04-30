# Néron × J.A.R.V.I.S — Intégration v2.0

## Analyse du repo source

**GauravSingh9356/J.A.R.V.I.S** est un assistant Python monolithique (2020, ~1 kloc)
qui couvre de nombreuses fonctionnalités utiles mais avec une architecture datée :
script unique, dépendances cloud/Windows, pas d'async, pas de tests.

### Ce qui vaut la peine d'être porté dans Néron

| Fonctionnalité JARVIS | Pertinence | Adaption Néron |
|---|---|---|
| News via NewsAPI | ✅ Haute | `NewsAgent` + RSS fallback (sans clé) |
| Météo OpenWeatherMap | ✅ Haute | `WeatherAgent` via Open-Meteo (0€, sans clé) |
| Todo list persistée | ✅ Haute | `TodoAgent` → SQLite `memory.db` existant |
| Recherche Wikipédia | ✅ Haute | `WikiAgent` + spell-check `difflib` |
| Spell-check `difflib` | ✅ Haute | Intégré dans `WikiAgent._spell_correct()` |
| Lecture heure/date | ✅ Déjà présent | `neron_time` existant |
| `psutil` ressources | ✅ Déjà présent | `SystemAgent` existant |
| Reconnaissance faciale | ❌ Bas | Hardware contraint, Telegram = auth suffisante |
| Envoi email `smtplib` | ⚠️ Moyen | `TwilioAgent` existant couvre ce besoin |
| YouTube search/dl | ⚠️ Moyen | Hors scope serveur (pas d'écran) |
| pyttsx3 TTS | ❌ Non | Hardware contraint (désactivé intentionnellement) |

---

## Fichiers générés

```
core/
├── constants.py                          ← MODIFIÉ — 4 nouveaux jeux de mots-clés
├── pipeline/
│   ├── intent/intent_router.py           ← MODIFIÉ — 4 nouveaux intents
│   └── routing/agent_router.py           ← MODIFIÉ — dispatch vers nouveaux agents
└── agents/
    ├── io/
    │   ├── news_agent.py                 ← NOUVEAU
    │   ├── weather_agent.py              ← NOUVEAU
    │   └── wiki_agent.py                 ← NOUVEAU
    ├── core/
    │   └── todo_agent.py                 ← NOUVEAU
    └── communication/
        └── telegram_patch.py             ← NOUVEAU (diff partiel)
```

---

## Installation des dépendances

Ajouter dans `requirements.txt` :

```
httpx>=0.27          # déjà présent — vérifier version
# Pas de nouvelle dépendance système requise !
# - Open-Meteo : gratuit, sans clé, sans pip supplémentaire
# - Nominatim  : idem
# - Wikipédia  : API publique, idem
# - NewsAPI    : optionnel (fallback RSS si absent)
```

---

## Configuration `neron.yaml` (optionnel)

```yaml
# Actualités
NEWS_API_KEY: ""          # Laisser vide → fallback RSS Le Monde (gratuit)
NEWS_COUNTRY: "fr"
NEWS_MAX_HEADLINES: 5

# Météo
WEATHER_DEFAULT_CITY: "Paris"
```

---

## Nouveaux intents disponibles

| Intent | Exemples de déclencheurs |
|---|---|
| `NEWS_QUERY` | "actualités", "les news", "quoi de neuf", "infos du jour" |
| `WEATHER_QUERY` | "météo", "température", "quel temps fait-il", "va-t-il pleuvoir" |
| `TODO_ACTION` | "ma liste", "ajoute à ma liste", "j'ai fait #3", "efface tout" |
| `WIKI_QUERY` | "qu'est-ce que", "définition de", "qui est", "/wiki" |

---

## Nouvelles commandes Telegram

| Commande | Description |
|---|---|
| `/news` | Actualités à la une |
| `/news tech` | Actualités tech |
| `/news france` | Actualités France |
| `/meteo` | Météo Paris (défaut) |
| `/meteo Lyon` | Météo Lyon |
| `/todo` | Afficher la liste |
| `/todo add Faire les courses` | Ajouter une tâche |
| `/todo done 3` | Marquer tâche #3 terminée |
| `/todo clear` | Supprimer les tâches terminées |
| `/wiki intelligence artificielle` | Résumé Wikipedia |

---

## Architecture — flux complet

```
[Telegram message]
    ↓
TelegramGateway
    ↓
IntentRouter.route()          ← intent_router.py
    ↓
AgentRouter.route()           ← agent_router.py
    ↓
NewsAgent / WeatherAgent / TodoAgent / WikiAgent
    ↓
[Réponse Telegram]
```

---

## Différences clés avec JARVIS

| JARVIS | Néron v2.0 |
|---|---|
| Monolithique (1 fichier) | Multi-agents modulaires |
| Synchrone | 100 % `async/await` |
| Cloud APIs obligatoires | Fallbacks gratuits (Open-Meteo, RSS, Wikipedia) |
| Windows/pyttsx3 | Linux/Ubuntu natif |
| Pas de mémoire entre sessions | SQLite persistant (`memory.db`) |
| Pas de web UI | Gateway WebSocket + Telegram |
