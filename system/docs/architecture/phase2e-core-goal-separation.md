# NéronOS — Phase 2E : séparation Core / Goal

Statut : **exécutée**
Mesures du 02/09/2026. Suite de
[phase2d-goal-boundary-decision.md](phase2d-goal-boundary-decision.md).

> **Règle désormais en vigueur :**
> Core ne sert pas Goal. Goal:8030 est l'unique propriétaire de l'API Goal.
> Core communique avec Goal via HTTP, par `server/common/goal_client`.
> Verrouillé par `tests/test_core_does_not_serve_goal.py`.

---

## 1. État avant

`server/core/app.py` chargeait deux routers du sous-module Goal via
`_EXTERNAL_ROUTER_SPECS` et les montait dans sa propre application :

```python
("goals",    "goal.goals.routes",    True)   → monté avec _INTERNAL_AUTH
("projects", "goal.projects.routes", False)  → monté sans dépendance
```

Core exposait ainsi **28 routes appartenant à Goal**, en plus de Goal lui-même.

## 2. Le problème

Trois conséquences, toutes mesurées :

1. **Double exécution.** Le code de Goal tournait *aussi* dans le process Core,
   avec ses propres singletons (`GoalManager`, `TaskManager`, `PlanStorage`)
   au-dessus du **même** stockage (`data/plans.jsonl`, SQLite). Le verrou de
   `PlanStorage` (`get_path_lock`) est un `threading.RLock` **in-process** : il
   ne protégeait rien entre les deux process.
2. **Création de tâches Goal dans Core.** `POST /goal` reçu par Core exécutait
   `get_goal_background_runner().submit(...)`, créant de vraies `asyncio.Task`
   Goal dans l'event loop de Core — d'où le `shutdown()` dans le `lifespan`
   de Core (site 19 du contrat Phase 2C).
3. **Angle mort du cliquet.** Ce couplage était **invisible** pour
   `tests/test_architecture_boundaries.py`, qui compte des imports AST : le
   montage passait par `importlib.import_module("goal.goals.routes")` —
   une *chaîne*, pas un import. Le compteur `core->goal` ne l'a jamais vu.

## 3. Inventaire des consommateurs

Recherche sur tout le dépôt (code, tests, scripts, systemd, Caddy, clients web,
documentation), au-delà des seuls imports Python.

| Fichier | Route | Type | Utilisation réelle | Action |
|---|---|---|---|---|
| `client/dashboard/src/lib/neronApi.ts:314` `sendGoal()` | `POST /goal` | F — code mort | fonction exportée, **jamais appelée** | aucune |
| `system/scripts/neron.sh:133` `cmd_goal` | `POST Core:8010/goal` | B — façade historique | **échouait déjà en 401** : pas de header d'auth alors que le router était monté derrière `_INTERNAL_AUTH` | migré vers Goal:8030 |
| `tests/test_internal_endpoint_auth.py` | `/projects`, `/goals` | D — échantillons obsolètes | routes utilisées comme exemples de surfaces protégées | échantillons retirés |
| `tests/test_async_goal_sqlite.py` | `/goal*`, `/goals` | — | cible l'app **Goal** (router importé directement) | aucune |
| `tests/test_goal_daemon.py` | `/goals*` | — | cible l'app **Goal** (`goal_app.app`) | aucune |
| `tests/test_core_orchestrator_authority.py:117` | `/projects` | E | **commande texte** dans l'aide, pas une route HTTP | aucune |
| `tests/test_goal_v2_provider_memory_api.py` | `/goal/v2` | F | `core.modules.goal_v2` **n'existe pas** ; 0 test collecté | préexistant, hors périmètre |
| `server/common/goal_client` | `/goals/*`, `/projects*` | — | vise déjà **Goal:8030** | conforme |
| Les 14 routes `/agents/*` de `goal/projects/routes.py` | — | F | **aucun consommateur** dans tout le dépôt | retrait sans impact |
| `client/dashboard` panneau Agents | `/self-model/agents` | A | route **Core native** (prefix `/self-model`) | aucune |
| `server/doctor` | `/health`, `/status` | A | ne sonde pas Goal du tout | à corriger (voir §8) |

**Conclusion : aucun consommateur fonctionnel ne dépendait des routes Goal
servies par Core.** Le seul appelant réel (`neron.sh`) était déjà cassé.

## 4. Routes retirées de Core

28 routes, toutes désormais servies uniquement par Goal:8030.

**`goal.goals.routes` (10)** — `POST /goal`, `POST /goals/run`, `GET /goals`,
`POST /goals`, `GET /goals/active`, `GET /goal/{id}/status`,
`GET /goal/{id}/events`, `POST /goals/{id}/complete`, `/fail`, `/progress`.

**`goal.projects.routes` (18)** — `GET /projects`, `/projects/search`,
`/projects/diagnostics/failures`, `/projects/{id}` ; `POST /agents/build`,
`POST /agents/proposals/{id}/approve`, `GET /agents`,
`GET|POST /agents/registry/scan`, `/agents/registry/index`,
`/agents/registry/diagnostics`, `GET /agents/{name}/status`,
`POST /agents/{name}/{inspect,revise,update,rename,delete,rollback}`.

**Conservées, car elles n'appartiennent pas à Goal :**
`POST /goals/active/task` (`core/api/goal_task_routes.py`, Core natif) et
`/agents/runtime/*` (`agents/runtime/routes.py`, plateforme `agents`).

## 5. Migrations effectuées

| Consommateur | Ancien | Nouveau |
|---|---|---|
| `system/scripts/neron.sh` (`neron goal "..."`) | `POST Core:8010/goal`, sans auth → **401** | `POST Goal:8030/goal` avec `Authorization: Bearer $NERON_API_KEY`, et message explicite si la clé manque |
| `core/app.py` `lifespan` | `get_goal_background_runner().shutdown()` | supprimé — plus aucune `asyncio.Task` Goal dans Core |
| `tests/test_internal_endpoint_auth.py` | `/goals`, `/projects` comme échantillons d'auth | échantillons retirés ; l'intention du test est préservée par les autres routes |
| `tests/test_command_dispatcher.py` | partait sur le réseau vers Goal:8030 | `_FakeGoalClient` injecté ; `FakeGoalOrchestrator` (jamais consulté) retiré |
| dashboard, doctor, Caddy, autres tests | — | **aucune migration nécessaire** |

## 6. Routes désormais exclusives à Goal

Vérifié sur l'application Core réelle (transport ASGI, clé valide) :

```
Core:8010                                    Goal:8030
  GET /goals              → 404                GET /goals              → 200
  GET /goals/active       → 404                GET /goals/active       → 200
  GET /goal/{id}/status   → 404                GET /projects           → 200
  GET /projects           → 404                GET /projects/search    → 200
  GET /projects/search    → 404                GET /tasks/summary      → 200
  GET /agents             → 404                GET /agents             → 200
  GET /agents/registry/*  → 404                GET /status, /health    → 200

  conservées :  GET /agents/runtime/status → 200
                POST /goals/active/task    → présent
```

## 7. Dépendances Core → Goal restantes

**Phase 2D : 22 → Phase 2E : 21.**

La baisse est faible *par construction* : le montage des routers passait par
une chaîne de caractères, invisible au compteur AST (§2.3). Le gain réel de
cette phase est la fin de la double exécution — 28 routes et tout un chemin
d'exécution supprimés du process Core — pas le delta du compteur. C'est
désormais `tests/test_core_does_not_serve_goal.py` qui verrouille ce point,
puisque le cliquet ne peut pas le voir.

Les 21 restantes, par blocage :

| Blocage | Sites | Ce qu'il faut |
|---|---|---|
| endpoint Goal manquant | 9 (`goal_task_routes` ×2, `planner_routes` ×6, `app.py` ×2 — `ensure_core_goals`, `recover_interrupted_goals`) | évolution de Goal (§D.3 du contrat 2C) |
| frontière sync/async | 4 (`goals_snapshot` ×3, `command_dispatcher` ×1) | décider si `GoalClient` gagne un mode synchrone, ou rendre la chaîne appelante asynchrone |
| objet manager passé à un tiers | 4 (`cognitive_core_routes` ×2, `cognitive_report_routes` ×2) | faire consommer un **dict** par `CognitiveCore` au lieu d'un manager |
| CRUD de plans | 1 (`planner_routes` `PlanStorage`) | évolution de Goal (§D.4 du contrat 2C) |
| healthcheck par importabilité | 1 (`modules/status/service.py`) | remplacer l'import par un ping HTTP `GET Goal:8030/status` |
| lecture de tâches | 1 (`self_model_routes`) | `GET /tasks/summary` existe déjà — bloqué par le sync/async |
| divers | 1 (`command_dispatcher` `get_goal_orchestrator`) | dépend des endpoints de plans |

## 8. Blockers pour la Phase 2F

1. **Aucune route réseau vers Goal.** Caddy ne route que `/api/*` → Core:8010 ;
   il n'existe **aucune** entrée vers Goal:8030. Tant que c'est le cas, aucun
   client web ne peut atteindre Goal, et la tentation de remettre un proxy
   dans Core restera. Décision à prendre : exposer Goal via Caddy, ou acter
   que Goal reste un service interne sans client web.
2. **Le sync/async de `GoalClient`** bloque 4 sites et conditionne tout appel
   depuis du code synchrone. À trancher avant d'attaquer les migrations
   restantes.
3. **Doctor ne surveille pas Goal.** Ses endpoints ne couvrent que Core, LLM et
   Ollama. Maintenant que Goal est seul à porter son API, une panne de
   Goal:8030 n'est détectée par rien.
4. **`GET /openapi.json` de Goal renvoie 500.** Le service répond correctement
   sur ses routes, mais son schéma OpenAPI est cassé — gênant dès lors qu'il
   devient l'API de référence.
5. **`tests/test_internal_endpoint_auth.py` est cassé pour une raison
   indépendante** : son fixture fait `monkeypatch.setattr(core_app,
   "world_model", ...)`, attribut qui n'existe pas (vérifié : absent aussi en
   `HEAD`). Les 9 tests du fichier échouent avant d'atteindre la moindre route.
   À réparer séparément.
