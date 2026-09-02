# NéronOS — Phase 2D : décision de frontière Core / Goal

Statut : **décisions prises, premier palier migré**
Mesures du 02/09/2026. Suite de
[phase2c-core-goal-http-contract.md](phase2c-core-goal-http-contract.md).

> Les mesures de ce document ont été prises **sur les services en cours
> d'exécution** (Core `127.0.1.1:8010`, Goal `127.0.1.3:8030`), pas seulement
> par lecture de code. Plusieurs conclusions de la Phase 2C sont corrigées
> ici en conséquence.

---

## 0. Le fait qui change tout : Core monte les routes de Goal

`server/core/app.py:139-148` (`_EXTERNAL_ROUTER_SPECS`) charge
`goal.goals.routes` et `goal.projects.routes`, et `app.py:710/721` les monte
réellement dans l'application Core.

Vérifié en production :

```
GET http://127.0.1.1:8010/goals/active  → 200   (Core)
GET http://127.0.1.3:8030/goals/active  → 200   (Goal)
        même goal_id, mêmes timestamps : même fichier sur disque
GET http://127.0.1.1:8010/route-inexistante → 404   (contrôle : le 200 ci-dessus est réel)
```

**Core n'importe pas seulement Goal : Core *sert* Goal.** Les deux process
répondent aux mêmes routes, avec deux jeux de singletons distincts
(`GoalManager`, `TaskManager`, `PlanStorage`) au-dessus du **même** stockage
(`data/plans.jsonl`, SQLite). Le verrou de `PlanStorage`
(`goal/infra/sqlite_store.py:27`, `get_path_lock`) est un `threading.RLock`
**in-process** : il ne protège rien entre Core et Goal.

C'est la cause dont les sites 19 et 26 du contrat Phase 2C sont les
symptômes. Les décisions ci-dessous en découlent.

---

## A. `background_runner.shutdown()` (site 19)

### Situation actuelle

| | |
|---|---|
| Définition | `goal/goals/background_runner.py` — `GoalBackgroundRunner`, singleton par process |
| État géré | `_tasks: dict[str, asyncio.Task]` — des tâches **de l'event loop du process courant** |
| Qui remplit `_tasks` | `goal/goals/routes.py:70` → `submit()`, sur `POST /goal` |
| Qui appelle `shutdown()` | `core/app.py:618-619`, dans le `finally` du `lifespan` |
| Autre consommateur | `modules/capabilities/resolver.py:614` (hors Core) |

### Analyse

L'hypothèse de la Phase 2C — « Goal tourne dans son propre process, donc ce
`shutdown()` depuis Core est probablement inutile » — est **fausse**.

Puisque Core monte `goal.goals.routes` (§0), un `POST /goal` reçu par Core
exécute `submit()` **dans le process Core** et y crée de vraies
`asyncio.Task`. Le `shutdown()` du `lifespan` de Core annule donc des
workflows bien réels, qui vivent dans Core. Le retirer laisserait des tâches
asyncio annulées brutalement à l'arrêt du process.

`shutdown()` est donc **correct**, et il est **au bon endroit** : un process
nettoie les tâches asyncio qu'il a lui-même créées. Ce n'est pas une
dépendance métier de Core envers Goal, c'est de l'hygiène de cycle de vie
d'un process qui héberge — à tort — du code Goal.

### Décision

**Conserver `background_runner.shutdown()` tel quel. Ne pas créer d'endpoint
HTTP.**

Un `POST /goals/shutdown` serait une faute d'architecture : Core n'a pas à
piloter l'arrêt de Goal, qui possède son propre cycle de vie systemd. Et
appeler un tel endpoint ne nettoierait pas les tâches du process Core — donc
il ne réglerait pas le problème qu'il prétend régler.

**Cette dépendance ne se migre pas : elle disparaît.** Le jour où Core cesse
de monter `goal.goals.routes`, plus aucune `asyncio.Task` Goal n'existe dans
Core, et l'appel devient un no-op à supprimer. Le site 19 est donc
reclassé : ce n'est pas une dépendance à convertir en HTTP, c'est un
**marqueur du montage en process** à retirer avec lui (Phase 2E).

### Justification

Migrer le symptôme avant la cause aurait produit un endpoint permanent pour
un besoin temporaire, tout en laissant le vrai problème (double exécution)
intact.

---

## B. `PlanStorage` factory (site 26)

### Situation actuelle

| | |
|---|---|
| Définition | `goal/planning/storage.py:20` — JSONL (`data/plans.jsonl`) + SQLite, verrou in-process |
| Site 26 | `core/orchestration/command_dispatcher.py:15` (import) et `:29` (`plan_storage_factory=PlanStorage`) |
| Usage réel du site 26 | **aucun** : assigné en `self.plan_storage_factory` (`:35`) et **jamais relu** dans le fichier |
| Passé par un appelant ? | **non** — 3 instanciations de `NeronCommandDispatcher` (2 tests + `:329`), aucune ne fournit ce paramètre |
| Autres usages de `PlanStorage` dans Core | `core/api/planner_routes.py:25` — instanciation module-level, **bien réelle** (site 9) |

### Analyse

Le site 26 est un paramètre d'injection **mort** : ni lu, ni fourni. Il n'y a
aucune opération métier derrière lui — donc **aucun endpoint Goal à en
déduire**. La Phase 2C le soupçonnait ; c'est confirmé.

À ne pas confondre avec le site 9 (`planner_routes.py`), lui bien vivant :
Core y instancie un `PlanStorage()` qui écrit dans le **même** `plans.jsonl`
et la **même** base SQLite que celui du process Goal, sans verrou partagé
(§0). Celui-là est un vrai problème de source de vérité — et le plus gros
morceau restant du contrat (§D.4 de la Phase 2C).

### Décision

**Retirer le paramètre `plan_storage_factory` et son import** dans
`command_dispatcher.py` : c'est du code mort, pas une frontière à contracter.
Gain : une dépendance Core → Goal en moins, à risque nul.

**Ne pas toucher au site 9** dans cette phase : il exige que Goal expose un
CRUD de plans (§D.4 Phase 2C), donc une évolution de Goal, hors périmètre.

### Justification

Créer un endpoint HTTP pour une injection jamais appelée aurait figé dans le
contrat une opération que personne ne demande.

---

## C. `core/api/task_routes.py` (sites 15 et 16)

### Situation actuelle

207 lignes, 16 routes, préfixe `/tasks`, toutes adossées à
`goal.system.task_manager.get_task_manager()` — aucune logique propre à Core.

**Trois routers revendiquent le préfixe `/tasks` :**

| Router | Concept de « task » | Monté dans Core ? |
|---|---|---|
| `core/api/task_routes.py` | tâches **Goal** | **non** |
| `modules/scheduler/routes.py` | tâches **planifiées** (scheduler) | oui |
| `goal/system/routes.py` | tâches **Goal** | dans le process Goal |

`core.api.task_routes` est bien **chargé** (`_CORE_ROUTER_SPECS`,
`app.py:130`) — son import de Goal compte donc dans le graphe — mais il n'est
**jamais monté** : il n'apparaît dans aucune des trois inclusions
(`app.py:704-726`, `1243`, `1247`).

### Preuve

```
GET /tasks/legacy          → 404      GET /tasks          → 200  (scheduler)
GET /tasks/legacy/schema   → 404      GET /tasks/status   → 200  (scheduler)
GET /tasks/legacy/status   → 404      GET /tasks/schema   → 200  (scheduler)
GET /tasks/legacy/running  → 404      GET /tasks/running  → 200  (scheduler)
```

Et surtout : `tests/test_fastapi_routing_audit.py::test_legacy_task_routes_are_not_registered`
**verrouille déjà** cette absence. La non-inclusion n'est pas un oubli, c'est
une décision antérieure, testée.

Conséquence visible en production, qui illustre la confusion des trois
`/tasks` :

```
GET Core:8010/tasks          → {"count":0,"tasks":[]}      (scheduler : 0 tâche planifiée)
GET Goal:8030/tasks/summary  → {"total":56,...}            (Goal : 56 tâches)
GET Core:8010/tasks/summary  → 404 "Scheduled task not found"
        ← le scheduler interprète "summary" comme un {task_id}
```

### Mapping Core ↔ Goal

| Route Core (`task_routes.py`) | Route Goal | Duplication | Source de vérité cible | Action |
|---|---|---|---|---|
| `GET /tasks/legacy` | — | morte | Goal | supprimer |
| `GET /tasks/legacy/status` | `GET /tasks/summary` | morte + dupliquée | Goal | supprimer |
| `GET /tasks/legacy/running` | — | morte | Goal | supprimer |
| `GET /tasks/legacy/next` | `GET /tasks/next` | morte + dupliquée | Goal | supprimer |
| `POST /tasks/legacy/next/start` | `POST /tasks/next/start` | morte + dupliquée | Goal | supprimer |
| `GET /tasks/legacy/schema` | — | morte | Goal | supprimer |
| `GET /tasks/legacy/{id}` | — | morte | Goal | supprimer |
| `POST /tasks/legacy/{id}/cancel` | — | morte | Goal | supprimer |
| `POST /tasks` | — | morte | Goal | supprimer |
| `PATCH /tasks/{id}/status` | — | morte | Goal | supprimer |
| `POST /tasks/{id}/start` | — | morte | Goal | supprimer |
| `POST /tasks/{id}/complete` | — | morte | Goal | supprimer |
| `POST /tasks/{id}/fail` | — | morte | Goal | supprimer |
| `DELETE /tasks/{id}` | — | morte | Goal | supprimer |
| `DELETE /tasks/done/clear` | — | morte | Goal | supprimer |

### Décision

**Cas A du périmètre — mais plus radical que prévu : le fichier n'est pas
seulement dupliqué, il est mort.** Supprimer `core/api/task_routes.py` et son
entrée dans `_CORE_ROUTER_SPECS`.

Aucun endpoint Goal n'est à créer pour autant : ces routes ne servent
personne aujourd'hui. Le §D.4 de la Phase 2C — présenté comme « le plus gros
morceau, CRUD complet à construire » — **perd ses sites 15 et 16** et se
réduit au seul site 9 (`PlanStorage` dans `planner_routes.py`).

Le jour où un CRUD de tâches devra être exposé, il devra l'être **par Goal**,
et Core n'en sera au mieux qu'un proxy — pas une seconde implémentation.

---

## D. Architecture cible

```
Core  (orchestration, interaction, gateway)
  │
  └── GoalClient            server/common/goal_client — unique point de couplage
        │
        ▼
      HTTP  (Bearer NERON_API_KEY)
        │
        ▼
  Goal :8030                gestion des goals / tasks / plans — SOURCE DE VÉRITÉ
```

Trois règles qui en découlent, dans l'ordre de priorité :

1. **Core ne sert pas Goal.** Tant que `_EXTERNAL_ROUTER_SPECS` monte
   `goal.goals.routes` et `goal.projects.routes`, tout le reste est
   cosmétique : c'est ce montage qui crée la double exécution, l'état
   dupliqué et les écritures concurrentes non verrouillées (§0).
2. **Core ne réimplémente pas Goal.** Un routeur Core qui ne fait que du CRUD
   sur un manager de Goal n'a pas de raison d'être (§C).
3. **Core lit Goal par HTTP.** Toute lecture d'état Goal passe par
   `GoalClient`, et un échec réseau devient une erreur explicite (503), pas
   une lecture silencieuse d'un état local dupliqué.

---

## E. Ordre de migration — corrigé par la mesure

Le §F de la Phase 2C annonçait 6 sites « migrables immédiatement »
(1, 3, 5, 13, 20, 24) au motif que `GET /goals/active` existe déjà. La
lecture ligne à ligne montre que **l'existence de l'endpoint n'était pas le
facteur limitant** : `GoalClient` est entièrement `async`, et la moitié de
ces sites vivent dans du code synchrone ou passent l'objet manager à un
tiers.

| Site | Fichier | Contexte réel | Migrable ? | Blocage |
|---|---|---|---|---|
| 1 | `api/cognitive_core_routes.py` | route async, mais passe l'**objet** `goal_system=` à `CognitiveCore` | non | l'objet est consommé dans `modules/cognitive_core`, pas ici — exige de changer l'interface de `CognitiveCore` |
| 3 | `api/cognitive_report_routes.py` | idem | non | idem |
| 5 | `api/goal_task_routes.py` | route async | non | couplé au site 6 (`create_task_from_goal`) : migrer seul donnerait une lecture distante + une écriture locale — pire que l'état actuel |
| 13 | `api/planner_routes.py:196` | route async, appel direct | **oui** | — |
| 20 | `modules/self_model/goals_snapshot.py:38` | fonction **sync** | non | frontière sync/async : `asyncio.run()` lèverait dans un event loop déjà actif |
| 24 | `orchestration/command_dispatcher.py:216` | méthode **sync** | non | idem |

**Un seul des six sites du « premier palier » est réellement migrable en
l'état.** C'est ce site qui a été migré (voir rapport de phase).

### Ce qui débloque le reste

| Blocage | Ce qu'il faut, et où |
|---|---|
| sync/async (sites 20, 24) | soit rendre asynchrone la chaîne appelante, soit doter `GoalClient` d'un mode synchrone. **Décision à prendre en 2E** : un client à deux visages est un coût permanent ; rendre `goals_snapshot` async touche le SelfModel. |
| objet passé (sites 1, 3) | faire consommer par `CognitiveCore` une **donnée** (dict) plutôt qu'un manager. Change une interface de `modules/`, pas de Goal. |
| endpoint manquant (sites 5+6, 7, 8, 10, 11, 12, 25) | évolution de `goal` (§D.3 Phase 2C) — hors périmètre tant que Goal n'est pas ouvert à modification |
| CRUD de plans (site 9) | évolution de `goal` (§D.4 Phase 2C) — le seul survivant du gros morceau |
| montage en process (site 19, cause de §0) | retirer `goal.goals.routes` / `goal.projects.routes` de `_EXTERNAL_ROUTER_SPECS`. **C'est le chantier central de la Phase 2E** : il supprime la double exécution, et fait tomber le site 19 sans écrire une ligne d'API. |

### Recommandation d'ordonnancement pour la Phase 2E

1. Retirer le montage en process des routers Goal dans Core (cause racine).
   Vérifier au préalable quels clients appellent aujourd'hui `Core:8010/goals/*`
   et `Core:8010/projects/*`, et les rediriger vers `Goal:8030`.
2. Trancher la question sync/async de `GoalClient` — elle bloque 2 sites et
   conditionne tous les futurs appels depuis du code synchrone.
3. Seulement ensuite, ouvrir `goal` aux endpoints manquants (§D.3), puis le
   CRUD de plans (§D.4).
