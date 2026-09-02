# NéronOS — Phase 2B : extraction du noyau et découplage de Core

Statut : **référence courante**
Mesures du 01/09/2026. Suite de [phase2a-core-decoupling.md](phase2a-core-decoupling.md).

---

## 1. Décisions appliquées

### SelfModel — Core est l'unique écrivain ✅

`neron-self-model-loop.service` : **arrêtée, désactivée, supprimée** (unité, module
`modules/self_model/self_model_loop.py`, entrée `Makefile`, contrat de test).

Vérifié avant suppression : la boucle n'apportait rien d'unique. Core appelle déjà
`refresh()` à la lecture (`self_model_routes`, `cognitive_core_routes`) et
`SelfMonitor` tourne dans Core. La boucle relançait toutes les 5 s des sondes HTTP
vers tous les services et deux `systemctl`, sur une machine à 2 cœurs.

Dans `core/modules/self_model/service.py` :

| | Avant | Après |
|---|---|---|
| État mutable | fichier, à chaque mutation | mémoire (`_mutable`) |
| Écritures par requête (`agent_router`) | **7** cycles lecture-modification-écriture (~50 Ko) | **0** |
| Persistance | boucle dédiée, 5 s | `refresh()`, bridée à **30 s** |
| Écrivains | 2 processus, sans verrou | **1** (Core) |

Mesuré en production après bascule : écritures du cache à 17:01:51, 17:02:35,
17:03:07 — l'intervalle de 30 s est respecté. `/self-model/*` répond 200.

### Identité — `NERON_IDENTITY_PATH` fait foi ✅ (mécanisme) / ⚠️ (contenu)

`core/identity/loader.py` codait son répertoire en dur et **ignorait totalement**
la variable. Corrigé :

* `identity_dir()` résout `NERON_IDENTITY_PATH` **à chaque appel** (pas de cache,
  sinon la variable reste inopérante) ;
* la variable désigne le `NERON.md` canonique, les documents compagnons vivent
  à côté ; un répertoire est également accepté ;
* défaut inchangé → **aucun changement de comportement en production** ;
* la clé `source` est réexposée : la provenance redevient vérifiable.

5 tests verrouillent ce mécanisme (`tests/test_identity_response.py`).

**Reste ouvert — décision humaine.** Deux `NERON.md` coexistent, dans **deux
formats incompatibles**, lus par **deux parsers** :

| | `core/identity/documents/NERON.md` | `memory/obsidian/identity/NERON.md` |
|---|---|---|
| Format | `clé: valeur` (`Name:`, `Rôle:`, `Mission:`) | titres Markdown (`# Mission`, `# Identité`) |
| Parser | `core/identity/loader.py` | `core/modules/identity/service.py` |
| Rôle | métadonnées d'identité + 3 documents compagnons | contexte opérationnel injecté dans les prompts |
| Consommateurs | `core.config`, `modules/{personality,sessions,skills}`, gateway | `modules/context/neron_context.py` |

Les deux sont vivants et servent des buts différents. Fusionner suppose de choisir
un format canonique **et** d'arbitrer le contenu (le second est plus riche sur la
mission). Rien n'a été supprimé.

### Goal — `core/goal_engine` n'est plus le moteur ⚠️ analysé, non exécuté

Voir §5.

---

## 2. Extraction du noyau — Runtime Governor

**Avant** : `core/runtime/governor.py`, importé par `modules` (3), `agents` (3),
`goal` (2), `tools` (1), plus Core.
**Après** : `server/common/runtime/governor.py`. Core conserve un
`TEMPORARY COMPATIBILITY SHIM` qui réexporte l'objet module d'origine — un seul
singleton `_governor`, quel que soit le chemin d'import (vérifié).

**Raison** : le governor autorise les commandes système *pour tout le monde*.
C'est une primitive de noyau, pas du Core.

**La difficulté, et sa résolution.** Le governor importait
`core.infrastructure.event_bus.Event`. Confiner cet import à `TYPE_CHECKING` ne
suffisait pas : le cliquet l'a **attrapé** et a fait entrer `common` dans le cycle.
Le noyau ne doit nommer aucun type de plateforme, même en annotation. La
dépendance a donc été remplacée par un **Protocol structurel défini dans le
noyau** :

```python
@runtime_checkable
class RuntimeEvent(Protocol):
    type: str
    payload: dict[str, Any] | None
```

Vérifié : l'`Event` de Core satisfait ce Protocol (`isinstance` → `True`), et
`server.common.runtime.governor` s'importe sans charger un seul module `core.*`.

**Impact mesuré** : `* → core` passe de **57 à 49** sites.
**Test** : `tests/test_architecture_boundaries.py` (5 tests), plus les 6 modules
migrés vérifiés à l'import, plus redémarrage de Core sans erreur.

---

## 3. `common` = puits architectural

Règle posée en Phase 2B et désormais **testée** :

```
plateformes  ──▶  common          autorisé, et recherché
common       ──▶  plateformes     interdit, sans exception
```

Le cliquet a été refondu en conséquence :

| Test | Rôle |
|---|---|
| `test_common_is_an_architectural_sink` | `common->*` doit être vide |
| `test_dependencies_on_core_do_not_grow` | **métrique centrale** : `* → core` ≤ 49 |
| `test_no_platform_edge_grows` | cliquet, **hors `->common`** : migrer vers le noyau fait mécaniquement monter `x->common` en faisant baisser `x->core`, c'est le mouvement voulu |
| `test_cycle_does_not_grow` | aucune plateforme nouvelle dans le cycle |
| `test_baseline_has_no_stale_entry` | une arête tombée à zéro sort de la référence |

---

## 4. Autonomous / Sandbox — correction de l'analyse Phase 2A

La Phase 2A comptait 10 sites (`core.autonomous` 7 + `core.runtime.sandbox` 3).
**`server/core/autonomous/` n'existe pas.**

Les 7 imports viennent de trois fichiers du parent —
`agents/autonomous/{self_healing,executor,supervisor}_agent.py` — qui sont
**inimportables** (`ModuleNotFoundError: No module named 'core.autonomous'`),
que **rien** n'importe, et qu'aucun chargement dynamique ne référence.

Ce n'est donc pas du couplage mais du **code mort**. Le couplage réel de cette
étape se limite à `core.runtime.sandbox.agent_sandbox` : 3 sites
(`agents/factory/build_orchestrator.py`, `agents/runtime/runtime.py`,
`modules/validation/business_validator.py`).

Ces trois fichiers morts implémentent l'auto-réparation et la supervision —
des rôles que l'architecture cible attribue à **Goal** et **Watchdog**. Les
supprimer ou les reprendre est une décision de produit, pas de refactoring : rien
n'a été supprimé.

---

## 5. Core → Goal : pourquoi l'étape n'a pas été exécutée

26 imports internes, 10 fichiers de Core, dominés par `get_goal_manager` (7) et
`get_task_manager` (6), puis `PlanStorage`, `get_goal_orchestrator`,
`get_goal_execution_engine`, `create_task_from_goal`, `AutonomousPlanner`,
`PlanExecutor`, `get_goal_background_runner`, `VALID_TASK_*`.

**Deux clients HTTP Goal existent déjà**, quasi dupliqués :

| | Emplacement | Méthodes | Utilisé par |
|---|---|---|---|
| `GoalClient` | `server/common/goal_client` — **bonne place (noyau)** | `run_goal`, `queue_goal`, `get_active_goal`, `get_goal_status`, `list_projects`, `search_projects`, `get_task_summary`, `get_next_task`, `start_next_task` | `core/pipeline/routing/agent_router.py` (10 sites) |
| `GoalService` | `core/pipeline/goal_client.py` | mêmes verbes, noms différents (`task_summary`, `next_task`, `find_projects`, `list_projects_sync`) | personne |

Le docstring de `GoalService` annonce lui-même remplacer « TOUS les imports
directs `from goal.…` du core » — travail jamais terminé.

**Blocage réel** : aucun des deux clients ne couvre les 26 usages. Ceux-ci
manipulent des **objets** (managers, storages, moteurs), pas des requêtes. Les
convertir suppose que le service Goal **expose les endpoints correspondants** —
c'est-à-dire du travail dans le sous-module `goal`, que la Phase 2B interdit
(« ❌ refonte Goal ») et qui relève du chantier propre à Goal.

Étape 6 **bloquée en amont**, pas oubliée. Préalable : arbitrer la surface HTTP
que Goal doit exposer. Prérequis mineur, faisable sans Goal : fusionner
`GoalService` dans `GoalClient` (noyau) pour n'avoir qu'un client.

---

## 6. Command dispatcher

Un seul consommateur hors de Core :
`agents/builtin/communication/telegram_agent.py` (import de module ligne 27,
import local ligne 465). L'inversion demandée §11 est donc **étroite** : elle ne
concerne qu'un fichier. La solution la plus simple compatible avec l'existant est
de faire descendre l'import de la ligne 27 au niveau de la fonction, comme le fait
déjà la ligne 465 — l'agent Telegram cesse alors de dépendre de Core à l'import.

Non exécuté : cela ne casse pas de cycle tant que `agents → core` subsiste par
ailleurs, et l'ordre imposé plaçait cette étape après les providers.

---

## 7. Ce qui reste à extraire

Chaîne de dépendances mesurée (elle impose l'ordre) :

```
identity  ──▶  (rien)                    259 l, 5 sites externes
config    ──▶  config.paths + identity   260 l, 10 sites
auth      ──▶  infrastructure.auth ──▶ config    4 sites
sqlite_store ──▶ config.paths            778 l, 2 sites
constants ──▶  (rien)                    195 l, 1 site
french_normalizer ──▶ (stdlib)           124 l, 1 site
```

`constants` et `french_normalizer` sont des feuilles pures : extractibles seules.
`identity → config → auth` forme une chaîne : à extraire dans cet ordre, d'un bloc.

**Doublon à traiter au passage** : `core/config/paths.py` est un fork de
`common/paths.py` (mêmes constantes à quelques-unes près). Son en-tête l'assume :
« formerly provided by common.paths. They now live in Core so core modules do not
depend on the legacy shared submodule ». C'est exactement l'inverse de la règle
posée en §3 : le noyau est partagé, Core en dépend.
