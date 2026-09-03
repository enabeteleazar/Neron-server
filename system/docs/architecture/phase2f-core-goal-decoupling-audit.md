# NéronOS — Phase 2F : audit de désolidarisation Core → Goal

Statut : **audit terminé, migrations non commencées**
Mesures du 03/09/2026. Suite de
[phase2e-core-goal-separation.md](phase2e-core-goal-separation.md).

> Référence architecturale : documentation **Notion** (décision du 03/09/2026).
> Ce document est une **mesure du code**, pas une architecture concurrente.

Décisions de cadrage retenues : client HTTP doté d'un **mode synchrone**
(pas de second client) ; **Goal non modifié** — les endpoints manquants sont
contractualisés, pas implémentés ; suppression du code mort **prouvé**
seulement ; migrations **progressives**, validées une par une.

---

## A. État actuel

| Phase | Imports Core → Goal |
|---|---|
| 2A (constat initial) | 26 |
| 2D (code mort retiré) | 22 |
| 2E (routers Goal démontés) | 21 |
| 2F (cet audit) | **21 — inventaire confirmé** |

**Couplage dynamique : nul.** Aucune chaîne `"goal.…"` ne subsiste dans Core,
aucun `importlib` ne vise Goal, aucune façade `sys.modules` ne pointe vers
Goal. C'est le point qui avait échappé au compteur AST en 2E ; il est
désormais vérifié explicitement.

---

## B. Les 21 dépendances

`ctx` = contexte d'exécution du **site d'appel** (et non de l'import).

| # | Fichier (server/core/) | L. | Symbole | ctx | Cat. |
|---|---|---|---|---|---|
| 1 | `api/cognitive_core_routes.py` | 6 | `get_goal_manager` | async | E |
| 2 | `api/cognitive_core_routes.py` | 8 | `get_task_manager` | async | E |
| 3 | `api/cognitive_report_routes.py` | 7 | `get_goal_manager` | async | E |
| 4 | `api/cognitive_report_routes.py` | 9 | `get_task_manager` | async | E |
| 5 | `api/goal_task_routes.py` | 7 | `get_goal_manager` | async | C |
| 6 | `api/goal_task_routes.py` | 8 | `create_task_from_goal` | async | C |
| 7 | `api/planner_routes.py` | 13 | `AutonomousPlanner` | async | C |
| 8 | `api/planner_routes.py` | 14 | `PlanExecutor` | async | C |
| 9 | `api/planner_routes.py` | 15 | `PlanStorage` | async | C |
| 10 | `api/planner_routes.py` | 16 | `get_task_manager` | async | C |
| 11 | `api/planner_routes.py` | 17 | `get_task_executor` | async | C |
| 12 | `api/planner_routes.py` | 19 | `get_goal_orchestrator` | async | C |
| 13 | `api/self_model_routes.py` | 8 | `get_task_manager` | **async** | **B** |
| 14 | `app.py` | 459 | `get_goal_execution_engine` | async | **G** |
| 15 | `app.py` | 460 | `get_goal_manager` | async | **G** |
| 16 | `modules/self_model/goals_snapshot.py` | 36 | `get_goal_manager` | sync | D→B |
| 17 | `modules/self_model/goals_snapshot.py` | 62 | `get_task_manager` | sync | D→B |
| 18 | `modules/self_model/goals_snapshot.py` | 48 | `get_goal_execution_engine` | sync | D→B |
| 19 | `modules/status/service.py` | 25 | `get_goal_orchestrator` | sync | D→B |
| 20 | `orchestration/command_dispatcher.py` | 12 | `get_goal_manager` | sync | D→B |
| 21 | `orchestration/command_dispatcher.py` | 13 | `get_goal_orchestrator` | sync | C |

Répartition : **B** migrable maintenant (1) · **D→B** débloqué par le mode
synchrone (5) · **C** endpoint Goal manquant (9) · **E** objet traversant la
frontière (4) · **G** décision architecturale (2). Aucun **A** (code mort) :
le ménage des phases 2C-2E a déjà tout retiré.

---

## C. Fiches par catégorie

### B — Migration directe (1 site)

**Site 13 — `api/self_model_routes.py:8`**
`get_task_manager().list_tasks()` puis `.list_active_tasks()`, dans une route
**déjà `async`** (`await _snapshot()` juste au-dessus). Sert à construire un
résumé de tâches pour `/self-model/context`.
→ `await client.get_task_summary()` sur `GET /tasks/summary`, **qui existe**.
Seul point de vigilance : le format. Core recompte les statuts lui-même,
Goal renvoie déjà `{total, active, running, pending, done, failed}`.
**Risque : faible.** Migrable immédiatement.

### D→B — Débloqués par le mode synchrone (5 sites)

Tous appellent Goal depuis du code **synchrone**. `asyncio.run()` y est
interdit (ces chemins sont invoqués depuis des routes déjà dans une boucle
d'événements : `RuntimeError: cannot be called from a running event loop`).

| Site | Appel réel | Endpoint | Existe ? |
|---|---|---|---|
| 16 | `get_active_goal()` (défensif, try/except) | `GET /goals/active` | ✅ |
| 18 | `get_goal_status(goal_id)` | `GET /goal/{id}/status` | ✅ |
| 17 | `list_tasks()` → recompte les statuts | `GET /tasks/summary` | ✅ |
| 19 | import seul, healthcheck par importabilité | `GET /status` | ✅ |
| 20 | `get_active_goal()` pour la commande `/goal` | `GET /goals/active` | ✅ |

**Les cinq endpoints existent déjà.** Le seul obstacle est la frontière
sync/async → levé par l'ajout d'un mode synchrone à `GoalClient`.

Le site 19 mérite une note : il ne lit aucune donnée, il teste si
`goal.goals.goal_orchestrator` est **importable** pour déclarer le
sous-système « available ». C'est un faux healthcheck — il mesure la présence
d'un fichier sur le disque de Core, pas la santé du service Goal:8030. Il
peut répondre « available » alors que Goal est arrêté.

### E — Objet Goal traversant la frontière (4 sites)

**Sites 1-4** — `cognitive_core_routes.py` et `cognitive_report_routes.py`
passent les **objets managers** à `CognitiveCore(goal_system=…,
task_manager=…)`, classe qui vit dans `server/modules/`.

Ce que `CognitiveCore` en fait réellement (duck typing, `hasattr`) :

| Sur `goal_system` | Sur `task_manager` |
|---|---|
| `get_active_goal()` | `list_active_tasks()` / `get_active_tasks()` |
| — | `list_tasks()` |
| — | **`create_task(...)`** ← écriture |

Donc **4 méthodes sur des objets entiers**. Un DTO ou un adaptateur mince
suffirait — l'objet manager complet n'est jamais nécessaire.

Deux difficultés à trancher avant de migrer :

1. `CognitiveCore` **écrit** (`create_task`) : ce n'est pas une simple
   lecture d'état, c'est une action métier qui appartient à Goal.
2. `CognitiveCore` vit dans `server/modules/` et importe lui-même
   `goal.system.task_manager` (lignes 15 et 375). Migrer les sites 1-4 sans
   traiter `modules → goal` déplacerait le couplage au lieu de le supprimer.

**Recommandation : ne pas migrer ces 4 sites en 2F.** Ils dépendent d'une
décision sur `server/modules` (dette n°2 : ~12 000 lignes de métier dans le
parent), pas sur Core.

### C — Endpoint Goal manquant (9 sites)

Aucun ne peut être migré sans faire évoluer Goal — hors périmètre (Q3=A).
Contrats proposés au §D.

- **5 + 6** (`goal_task_routes`) : lire l'objectif actif puis
  `create_task_from_goal()`. Indissociables : migrer 5 seul produirait une
  lecture distante suivie d'une écriture locale, pire que l'état actuel.
- **7-12** (`planner_routes`) : `AutonomousPlanner`, `PlanExecutor`,
  `PlanStorage`, `TaskManager`, `TaskExecutor`, `GoalOrchestrator`. C'est le
  bloc le plus dense : la totalité du cycle plan/tâche s'exécute en processus
  dans Core.
- **21** (`command_dispatcher`) : `find_plan` / `execute_approved_plan` /
  `execute_plan` pour les commandes `/approve` et `/execute`.

`PlanStorage` (site 9) reste le point le plus sensible : Core en instancie un
au niveau module, qui écrit dans le **même** `data/plans.jsonl` et la **même**
base SQLite que le processus Goal. Le verrou (`get_path_lock`) est un
`threading.RLock` **in-process** : il ne protège rien entre les deux
processus.

### G — Décision architecturale (2 sites)

**Sites 14-15 — `app.py:459-460`** dans le `lifespan` de Core :

```python
get_goal_manager().ensure_core_goals()
get_goal_execution_engine().recover_interrupted_goals()
```

Constat : **`server/goal/app.py` ne possède aucun `lifespan` ni handler de
démarrage**, et ces deux méthodes ne sont appelées **que depuis Core**.

Autrement dit, **Core effectue le démarrage de Goal**, dans son propre
processus, et l'effet ne devient visible pour le vrai service Goal que parce
que les deux partagent le même stockage sur disque.

⚠️ Le contrat de la Phase 2C proposait ici `POST /goals/ensure-core` et
`POST /goals/recover-interrupted`. **Cette proposition est erronée et doit
être retirée** : elle graverait dans le contrat le fait que Core pilote
l'initialisation de Goal. Le correctif juste est que **Goal s'initialise
lui-même dans son propre `lifespan`** — une modification de Goal, donc hors
périmètre de cette phase, mais à inscrire comme prérequis.

---

## D. Contrats des endpoints manquants

À implémenter **dans Goal**, hors de cette phase. Authentification :
`Authorization: Bearer $NERON_API_KEY`, comme les routes existantes.

| Endpoint | Méthode | Remplace | Entrée | Sortie | Erreurs |
|---|---|---|---|---|---|
| `/goals/active/task` | POST | 5+6 | — | `{created, source, goal, task}` | 404 aucun objectif actif |
| `/planner/create` | POST | 7 | `{objective}` | `Plan` | 422 objectif vide |
| `/planner/execute/{plan_id}` | POST | 8 | — | `Plan` | 404 |
| `/plans` | GET/POST | 9 | filtre / `Plan` | liste / `Plan` | — |
| `/plans/{id}` | GET/PATCH | 9 | — / patch | `Plan` | 404 |
| `/plans/last`, `/plans/history` | GET | 9 | — | `Plan` / liste | — |
| `/tasks` (liste), `/tasks/active` | GET | 10, 17 | `status?` | `{count, tasks}` | — |
| `/tasks/from-plan/{plan_id}` | POST | 10 | — | `{tasks}` | 404 |
| `/tasks/next/execute`, `/tasks/{id}/execute` | POST | 10, 11 | — | `Task` | 404 |
| `/goals/plans/{id}` | GET | 21 | — | `Plan` | 404 |
| `/goals/plans/{id}/execute-approved` | POST | 12, 21 | `{approved_by}` | `Plan` | 404, 409 non approuvé |
| `/goals/plans/{id}/sync-tasks` | POST | 12 | — | `{plan, tasks}` | 404 |

**Retiré du contrat 2C** : `POST /goals/ensure-core` et
`POST /goals/recover-interrupted` (voir catégorie G — c'est un `lifespan`
dans Goal qu'il faut, pas un endpoint).

---

## E. Plan de migration proposé

Progressif, chaque palier testé et validé avant le suivant.

**Palier 1 — `GoalClient` gagne un mode synchrone.**
Étendre le client existant (pas de second client) avec un `httpx.Client` et
les méthodes synchrones strictement nécessaires : `get_active_goal_sync`,
`get_goal_status_sync`, `get_task_summary_sync`, `ping_sync`. Aucune
migration dans ce palier : uniquement l'outil et ses tests.
Débloque 5 sites. **Risque : faible.**

**Palier 2 — site 13** (`self_model_routes`), migration async directe.
Endpoint existant, contexte déjà asynchrone. **Risque : faible.**

**Palier 3 — sites 16, 17, 18, 20** via le mode synchrone.
Lectures d'état, toutes déjà défensives (`try/except`). **Risque : faible.**

**Palier 4 — site 19**, le healthcheck : remplacer l'import par un ping HTTP
`GET Goal:8030/status`. Corrige un faux positif (Goal peut être arrêté et
déclaré « available »). **Risque : moyen** — change la sémantique de
`/status`, et un Goal lent rendra Core plus lent : timeout court obligatoire.

**Palier 5 — non exécuté en 2F.** Sites 5-12, 21 (endpoints Goal manquants),
1-4 (dépendent de `server/modules`), 14-15 (dépendent d'un `lifespan` dans
Goal).

**Résultat attendu à l'issue des paliers 1-4 : 21 → 15 sites.**

---

## F. Ce qui doit rester interdit

- Créer dans Core un `GoalManager`, `TaskManager`, `PlanStorage`,
  `GoalOrchestrator` ou `GoalExecutionEngine`, même partiel.
- Faire de Core un proxy HTTP de Goal (route Core qui relaie vers Goal:8030).
- Créer un second client HTTP concurrent de `server/common/goal_client`.
- Ajouter un second écrivain au SelfModel : Core reste seul écrivain, Goal
  lit.
