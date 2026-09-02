# NéronOS — Phase 2C : contrat HTTP Core → Goal

Statut : **proposition technique, non implémentée**
Mesures du 02/09/2026. Suite de [phase2b-kernel-extraction.md](phase2b-kernel-extraction.md) §5.

> Ce document décrit l'API que le service `goal` (port 8030) devrait exposer
> pour couvrir les 26 imports en processus que Core fait aujourd'hui vers les
> internes de `goal`. **Aucun endpoint proposé ici n'a été implémenté** : le
> sous-module `goal` n'a pas été modifié pendant cette phase (règle explicite
> de la Phase 2C).

---

## A. Objectif

`goal` est un service HTTP séparé, avec son propre port (8030) et son propre
process. Core devrait donc lui parler **uniquement** en HTTP, via
`server/common/goal_client`. Ce n'est pas le cas : `server/core` importe
directement 26 fois des objets internes de `goal` (managers, storages,
moteurs — `GoalManager`, `TaskManager`, `PlanStorage`, `GoalOrchestrator`,
`GoalExecutionEngine`, `AutonomousPlanner`, `PlanExecutor`…).

Conséquence mesurée en Phase 2A (§6, « Core ↔ Goal — contrat violé ») : le
code de `goal` s'exécute **deux fois en parallèle** — une fois dans le
process `goal` réel, une fois importé à froid dans le process `core`, avec
son propre état (ses propres singletons `GoalManager`/`TaskManager`, sa
propre connexion SQLite). Les deux copies divergent silencieusement. C'est la
violation de contrat la plus grave de l'inventaire Core ↔ parent.

Ce document ne corrige pas la violation — corriger `goal` est hors périmètre
de cette phase. Il produit le **contrat cible** : quel endpoint HTTP
remplacerait quel import, pour que la Phase 2D (ou une phase ultérieure)
puisse faire le remplacement sans redécouvrir l'inventaire à zéro.

---

## B. API Goal existante

Service `goal`, port 8030, monté par `server/goal/app.py`. Trois routers +
une route de statut locale. Authentification : `Authorization: Bearer
$NERON_API_KEY` (`Depends(require_api_key)`) sur toutes les routes sauf
`/health` et `/status` (sondes watchdog, ouvertes sans auth). Si
`NERON_API_KEY` n'est pas définie côté serveur, le mode est ouvert (avec
avertissement au démarrage). Pas de format d'erreur uniforme : chaque handler
retourne son propre `detail` via `HTTPException` (422 validation légère faite
à la main, 404 ressource absente, 409 conflit d'état).

### Routes déjà montées

| Méthode | Chemin | Fichier | Résumé |
|---|---|---|---|
| GET | `/health` | `common/service.py` (`create_service_app`) | Sonde standard : service, version, uptime, `registered` |
| GET | `/status` | `goal/app.py:65` | `{service, status, uptime, goal_count}` |
| POST | `/goals/run` | `goal/goals/routes.py:45` | Exécution **synchrone** d'un objectif (bloque jusqu'au verdict) |
| POST | `/goal` | `goal/goals/routes.py:54` | File d'attente **asynchrone**, réponse 202 |
| GET | `/goals` | `goal/goals/routes.py:83` | Liste fusionnée `execution_engine` + `goal_manager` legacy |
| GET | `/goals/active` | `goal/goals/routes.py:94` | Objectif actif |
| GET | `/goal/{goal_id}/status` | `goal/goals/routes.py:99` | Statut détaillé, 404 si absent |
| GET | `/goal/{goal_id}/events` | `goal/goals/routes.py:107` | Événements d'exécution |
| POST | `/goals` | `goal/goals/routes.py:115` | Création manuelle (legacy `GoalManager`) |
| POST | `/goals/{goal_id}/complete` | `goal/goals/routes.py:127` | — |
| POST | `/goals/{goal_id}/fail` | `goal/goals/routes.py:135` | — |
| POST | `/goals/{goal_id}/progress` | `goal/goals/routes.py:143` | — |
| GET | `/projects` | `goal/projects/routes.py:75` | Liste, filtrable par statut |
| GET | `/projects/search` | `goal/projects/routes.py:82` | Recherche par requête `q` |
| GET | `/projects/diagnostics/failures` | `goal/projects/routes.py:89` | — |
| GET | `/projects/{project_id}` | `goal/projects/routes.py:95` | 404 si absent |
| POST | `/agents/build` + `/agents/*` | `goal/projects/routes.py:104-348` | Usine à agents (build, approve, list, registry, CRUD) |
| GET | `/tasks/summary` | `goal/system/routes.py:26` | Compteurs par statut/priorité, aplatis |
| GET | `/tasks/next` | `goal/system/routes.py:43` | 404 si aucune tâche pending |
| POST | `/tasks/next/start` | `goal/system/routes.py:51` | 404 si rien à démarrer |

`server/goal/projects/routes_basic.py` existe mais **n'est jamais monté**
(code mort, hors périmètre de suppression de cette phase — signalé au §12
du rapport final).

### Ce que `GoalClient` (le client déjà correct) consomme aujourd'hui

`server/common/goal_client/__init__.py` (base `http://127.0.1.3:8030`) :
`run_goal`, `queue_goal`, `get_active_goal`, `get_goal_status`,
`list_projects`, `search_projects`, `get_task_summary`, `get_next_task`,
`start_next_task`. **9 méthodes sur ~26 opérations réellement utilisées par
Core.**

---

## C. Les 26 dépendances actuelles

Périmètre : `server/core/**/*.py`, imports `from goal.*`. Confirmé exhaustif
par deux passes indépendantes (Phase 2B et cet audit) : **26 sites, 10
fichiers**, aucune divergence.

| # | Fichier Core | Ligne | Symbole importé | Usage réel | Opération métier |
|---|---|---|---|---|---|
| 1 | `api/cognitive_core_routes.py` | 6 | `goal.goals.goal_manager.get_goal_manager` | `.get_active_goal()` via `CognitiveCore.goal_system` | Objectif actif pour l'état cognitif agrégé |
| 2 | `api/cognitive_core_routes.py` | 8 | `goal.system.task_manager.get_task_manager` | `.list_active_tasks()` via `CognitiveCore.task_manager` | Tâches actives pour l'état cognitif |
| 3 | `api/cognitive_report_routes.py` | 7 | `goal.goals.goal_manager.get_goal_manager` | idem #1, pour le rapport texte | Objectif actif dans le rapport cognitif |
| 4 | `api/cognitive_report_routes.py` | 9 | `goal.system.task_manager.get_task_manager` | idem #2, pour le rapport texte | Tâches actives dans le rapport cognitif |
| 5 | `api/goal_task_routes.py` | 7 | `goal.goals.goal_manager.get_goal_manager` | `.get_active_goal()` | Lecture de l'objectif courant |
| 6 | `api/goal_task_routes.py` | 8 | `goal.system.goal_task_bridge.create_task_from_goal` | fonction pure, appelée sur l'objectif actif | Pont goal→task (logique métier interne à `goal`) |
| 7 | `api/planner_routes.py` | 13 | `goal.planning.AutonomousPlanner` | `.create_plan(goal)` | Planification automatique d'un objectif |
| 8 | `api/planner_routes.py` | 14 | `goal.planning.executor.PlanExecutor` | `.execute(plan)` (route legacy) | Exécution directe d'un plan |
| 9 | `api/planner_routes.py` | 15 | `goal.planning.storage.PlanStorage` | CRUD complet (`save/update/get/last/history`) sur presque toutes les routes `/planner/*` | Persistance/lecture/approbation des plans |
| 10 | `api/planner_routes.py` | 16 | `goal.system.task_manager.get_task_manager` | `.create_tasks_from_plan/.next_active_task/.update_task/.get_task/.fail_task` (+ `._now()` privé) | Cycle tâche↔plan |
| 11 | `api/planner_routes.py` | 17 | `goal.system.task_executor.get_task_executor` | `.execute(task)` | Exécution d'une tâche unitaire |
| 12 | `api/planner_routes.py` | 19 | `goal.goals.goal_orchestrator.get_goal_orchestrator` | `.sync_plan_task_status()`, `.execute_approved_plan()` | Exécution contrôlée + réconciliation plan/tâches |
| 13 | `api/planner_routes.py` | 20 | `goal.goals.goal_manager.get_goal_manager` | `.get_active_goal()` | Bootstrap d'un plan depuis l'objectif courant |
| 14 | `api/self_model_routes.py` | 8 | `goal.system.task_manager.get_task_manager` | `.list_tasks()/.list_active_tasks()` | Résumé de tâches pour le contexte self-model |
| 15 | `api/task_routes.py` | 9 | `goal.system.task_manager.get_task_manager` | quasi toute l'API CRUD (`update_status, list_tasks, get_status_summary, list_running_tasks, get_next_task, start_next_task, create_task, get_task, delete_task, clear_done`) | Router `/tasks` complet, dupliqué avec `goal/system/routes.py` |
| 16 | `api/task_routes.py` | 10 | `goal.system.task_model.VALID_TASK_PRIORITIES / VALID_TASK_STATUSES` | Constantes exposées par `GET /tasks/legacy/schema` | Métadonnées de schéma |
| 17 | `app.py` | 457 | `goal.goals.execution_engine.get_goal_execution_engine` | `.recover_interrupted_goals()` au démarrage (`lifespan`) | Reprise après crash |
| 18 | `app.py` | 458 | `goal.goals.goal_manager.get_goal_manager` | `.ensure_core_goals()` au démarrage | Initialisation idempotente des goals système |
| 19 | `app.py` | 618 | `goal.goals.background_runner.get_goal_background_runner` | `await .shutdown()` à l'arrêt | Arrêt propre des workflows async |
| 20 | `modules/self_model/goals_snapshot.py` | 36 | `goal.goals.goal_manager.get_goal_manager` | `.get_active_goal()` (défensif, try/except) | Snapshot self-model : objectif actif |
| 21 | `modules/self_model/goals_snapshot.py` | 48 | `goal.goals.execution_engine.get_goal_execution_engine` | `.get_goal_status(goal_id)` | Snapshot self-model : statut d'exécution détaillé |
| 22 | `modules/self_model/goals_snapshot.py` | 62 | `goal.system.task_manager.get_task_manager` | `.list_tasks()` | Snapshot self-model : état des tâches |
| 23 | `modules/status/service.py` | 25 | `goal.goals.goal_orchestrator.get_goal_orchestrator` (`# noqa: F401`) | **import seul**, healthcheck par importabilité | Disponibilité du sous-système goal pour `/status` |
| 24 | `orchestration/command_dispatcher.py` | 12 | `goal.goals.goal_manager.get_goal_manager` | factory par défaut → `.get_active_goal()` | Commande `/goal` (affichage objectif actif) |
| 25 | `orchestration/command_dispatcher.py` | 13 | `goal.goals.goal_orchestrator.get_goal_orchestrator` | factory par défaut → `.find_plan()/.execute_approved_plan()/.execute_plan()` | Commandes `/approve`, `/execute` (humain dans la boucle) |
| 26 | `orchestration/command_dispatcher.py` | 15 | `goal.planning.storage.PlanStorage` | factory par défaut, **aucun appel constaté dans ce fichier** | Injection de dépendance non utilisée localement |

Répartition par symbole dominant : `get_goal_manager` **7**, `get_task_manager`
**6**, `get_goal_orchestrator` **3**, `PlanStorage` **2**,
`get_goal_execution_engine` **2**, et 1 site chacun pour
`create_task_from_goal`, `AutonomousPlanner`, `PlanExecutor`,
`get_task_executor`, `get_goal_background_runner`,
`VALID_TASK_PRIORITIES`/`VALID_TASK_STATUSES`.

Hors périmètre strict `server/core` mais mesuré au passage avec le même
motif : 16 sites additionnels dans `server/modules/**` et 7 dans
`server/agents/**` importent aussi `goal.*` directement. Le couplage réel
dépasse donc `core`, mais seul `core → goal` est dans le périmètre imposé de
cette phase.

---

## D. API cible proposée

Classée par ce qui existe déjà, ce qui s'ajoute sans logique nouvelle côté
`goal` (juste exposer un endpoint sur du code déjà présent), et ce qui exige
une vraie évolution de `goal`.

### D.1 — Déjà couvert par une route existante (aucune évolution `goal` requise)

| Ancien import | Endpoint existant | Sites couverts |
|---|---|---|
| `get_goal_manager().get_active_goal()` | `GET /goals/active` | 1, 3, 5, 13, 20, 24 |
| `get_goal_execution_engine().get_goal_status(id)` | `GET /goal/{goal_id}/status` | 21 |
| import seul (healthcheck) | `GET /status` (ping HTTP au lieu d'un import) | 23 |

### D.2 — Nouveaux endpoints simples (exposition directe de code déjà présent dans `goal`)

| Endpoint proposé | Méthode | Remplace | Request | Response | Erreurs |
|---|---|---|---|---|---|
| `/tasks/active` | GET | 2, 4 | — | `{count, tasks: Task[]}` | — |
| `/tasks` (liste complète, pas juste `/next`) | GET | 14, 22 | query `status?` | `{count, tasks: Task[]}` | — |
| `/tasks/schema` | GET | 16 | — | `{statuses: [...], priorities: [...]}` | — |
| `/goals/recover-interrupted` | POST | 17 | — | `{recovered: int}` | 500 si le moteur échoue |
| `/goals/ensure-core` | POST | 18 | — | `{goals: Goal[]}` | — |

### D.3 — Nouveaux endpoints qui exposent une opération métier existante (le service `goal` exécute lui-même la logique qu'il exécute déjà en interne)

| Endpoint proposé | Méthode | Remplace | Request | Response | Erreurs |
|---|---|---|---|---|---|
| `POST /goals/active/task` | POST | 5 + 6 (combinés) | — | `{created, source, goal, task}` | 404 si aucun objectif actif |
| `POST /planner/create` | POST | 7 | `{objective: str}` | `Plan` sérialisé | 422 si objectif vide |
| `POST /planner/execute/{plan_id}` | POST | 8 (legacy) | — | `Plan` mis à jour | 404 si plan absent |
| `POST /tasks/from-plan/{plan_id}` | POST | 10 (génération) | — | `{tasks: Task[]}` | 404 si plan absent |
| `POST /tasks/next/execute` | POST | 10 (exécution séquentielle) + 11 | — | `Task` mis à jour | 404 si aucune tâche |
| `POST /tasks/{task_id}/execute` | POST | 11 | — | `Task` mis à jour | 404 si tâche absente |
| `POST /goals/plans/{plan_id}/execute-approved` | POST | 12, 25 | `{approved_by: str}` | `Plan` mis à jour | 409 si pas approuvé |
| `POST /goals/plans/{plan_id}/sync-tasks` | POST | 12 | — | `{plan, tasks}` | 404 |
| `GET /goals/plans/{plan_id}` | GET | 25 (`find_plan`) | — | `Plan` | 404 |
| `POST /goals/plans/{plan_id}/execute` | POST | 25 (`execute_plan`, hors approbation) | — | `Plan` mis à jour | 404, 409 |

### D.4 — CRUD complet à exposer (le plus gros morceau : `PlanStorage` et `TaskManager`)

| Endpoint proposé | Méthode | Remplace | Note |
|---|---|---|---|
| `GET /plans` | GET | 9 (liste) | pagination à définir |
| `POST /plans` | POST | 9 (save) | |
| `GET /plans/{id}` | GET | 9 (get) | 404 |
| `PATCH /plans/{id}` | PATCH | 9 (update) | |
| `GET /plans/last` | GET | 9 (last) | |
| `GET /plans/history` | GET | 9 (history) | |
| `POST /tasks` | POST | 15 (create_task) | déjà quasi-dupliqué entre `core/api/task_routes.py` et `goal/system/routes.py` — **fusionner, pas juste migrer** |
| `PATCH /tasks/{id}/status` | PATCH | 15 (update_status) | |
| `POST /tasks/{id}/start` \| `/complete` \| `/fail` | POST | 15 | |
| `DELETE /tasks/{id}` | DELETE | 15 (delete_task) | |
| `DELETE /tasks/done/clear` | DELETE | 15 (clear_done) | |

### D.5 — À reconsidérer plutôt qu'à migrer telle quelle

- **Site 26** (`PlanStorage` factory dans `command_dispatcher.py`, jamais
  appelée dans ce fichier) : pas d'opération métier active constatée. Ne pas
  créer d'endpoint pour un usage qui n'existe pas — vérifier d'abord si
  l'injection sert ailleurs (tests ?) avant de la retirer.
- **Site 19** (`background_runner.shutdown()`) : `goal` tourne en process
  séparé avec son propre cycle de vie systemd. Un `POST /goals/shutdown`
  appelé depuis le `lifespan` de Core n'a de sens que si Core doit
  **attendre** que `goal` finisse ses workflows avant de couper le réseau —
  à confirmer avec l'humain plutôt qu'à supposer.
- **Sites 15/16** (`core/api/task_routes.py`) : ce fichier expose déjà un
  router `/tasks` complet **dans Core**, qui deviendrait un simple proxy HTTP
  vers `goal`. Question ouverte : ce routeur doit-il continuer d'exister côté
  Core (façade HTTP publique inchangée pour les clients existants du Core)
  ou disparaître au profit d'un accès direct à `goal:8030` ? Décision produit,
  pas technique.

---

## E. Mapping — ancien import interne → GoalClient → endpoint HTTP

```
core.api.cognitive_core_routes                 core.api.planner_routes
  from goal.goals.goal_manager                   from goal.planning.storage import PlanStorage
       import get_goal_manager                        PlanStorage().save(plan) / .get(id) / ...
            │                                               │
            ▼                                               ▼
  GoalClient.get_active_goal()                  GoalClient.get_plan(id) / .save_plan(plan) / ...
            │                                     (methodes A CREER sur GoalClient)
            ▼                                               │
  GET http://goal:8030/goals/active                         ▼
                                                 GET/POST/PATCH http://goal:8030/plans[/{id}]
```

Principe général, appliqué aux 26 sites du §C : chaque `from goal.X import Y`
suivi d'un appel `Y().méthode(...)` devient un appel de méthode sur
`GoalClient` (à étendre — aujourd'hui 9 méthodes, il en faudrait ~20 pour
couvrir le §D), qui fait un `httpx` vers l'endpoint correspondant du §D.
`GoalClient` reste l'unique point de couplage HTTP ; aucun fichier de `core`
ne doit plus écrire `from goal...` après migration — c'est le critère de
sortie de la Phase 2D/2E sur ce chantier.

Détail ligne à ligne : voir tableau du §C, colonne « Endpoint HTTP Goal
suggéré » (reporté dans le corps de chaque ligne du §D selon le groupe D.1
à D.5).

---

## F. Ordre de migration proposé

1. **Sans aucune évolution de `goal`** — bascule immédiate possible dès que
   `GoalClient` est étendu avec `get_active_goal()` (existe déjà) : sites 1,
   3, 5 (partiel), 13, 20, 24. Le plus petit risque, le plus grand nombre de
   sites déjà couverts par une route existante.
2. **Évolution mineure de `goal`** (exposer un endpoint sur du code déjà
   présent, sans changer sa logique) — §D.1 et D.2 : sites 2, 4, 14, 16, 17,
   18, 21, 22, 23. Risque faible : pas de nouvelle logique métier, juste un
   `@router.get/post` de plus.
3. **Évolution moyenne** (le service exécute une opération qu'il exécute déjà
   en interne, mais pas encore accessible depuis l'extérieur) — §D.3 : sites
   6, 7, 8, 10 (partiel), 11, 12, 25.
4. **Évolution lourde** (CRUD complet à construire, fusion avec le routeur
   `/tasks` déjà dupliqué côté Core) — §D.4 : sites 9, 10 (partiel), 15, 16.
   C'est le morceau qui justifie une itération dédiée : `PlanStorage` est
   consommé par presque toutes les routes de `planner_routes.py`, et
   `core/api/task_routes.py` duplique déjà une partie de ce que `goal/system/
   routes.py` devrait exposer — les fusionner évite de migrer un doublon.
5. **Décision humaine avant migration** — §D.5 : sites 19, 26. Pas un
   problème technique : il manque une décision produit (Core doit-il
   attendre l'arrêt de `goal` ? le routeur `/tasks` de Core doit-il
   survivre ?).

Aucune de ces étapes n'a été exécutée pendant la Phase 2C : c'est le travail
de la Phase 2D, une fois ce contrat validé par un humain.
