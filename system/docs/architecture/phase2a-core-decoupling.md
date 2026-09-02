# NéronOS — Phase 2A : découplage architectural de Core

Statut : **référence courante**
Mesures du 31/08/2026. Complète [neronos-architecture.md](neronos-architecture.md).

> **Mis à jour par la Phase 2B** ([phase2b-kernel-extraction.md](phase2b-kernel-extraction.md)).
> Deux corrections à ce document : (1) `* → core` est passé de 57 à **49** sites
> après extraction du Runtime Governor ; (2) les 7 sites `core.autonomous`
> comptés au §3 n'existent pas — `server/core/autonomous/` est absent et les
> trois fichiers du parent qui l'importent sont du code mort inimportable.


---

## 1. Ce que Core possède réellement

Core pèse **~19 600 lignes**. Classement par responsabilité réelle :

| Paquet | Lignes | Responsabilité réelle | Verdict |
|---|---|---|---|
| `pipeline` | 4 491 | ORCHESTRATION + DOMAIN LOGIC (NLP, intent, routing) | **reste**, sauf le normaliseur FR → noyau |
| `modules` | 3 541 | SELF-MODEL (1 459), identity (635), status (399), memory (423), knowledge (216), timer (91) | self_model **reste** ; identity → noyau ; memory → Memory |
| `goal_engine` | 1 740 | **GOAL LOGIC** | → Goal |
| `gateway` | 1 727 | COMMUNICATION | **reste** |
| `providers` | 1 262 | CAPABILITY (contrats de providers) | → contrats partagés |
| `api` | 1 169 | COMMUNICATION | **reste** |
| `runtime` | 1 168 | SECURITY (governor, sandbox d'agents) | governor → noyau ; sandbox → agents |
| `infrastructure` | 971 | LIFECYCLE / OBSERVABILITY / SECURITY | → noyau |
| `storage` | 781 | CONFIGURATION (SQLite) | → noyau |
| `orchestration` | 357 | ORCHESTRATION | **reste** |
| `identity` | 259 | DOMAIN LOGIC (corpus d'identité) | → noyau |
| `control_plane` | 244 | ORCHESTRATION | **reste** |
| `a2a` | 176 | COMMUNICATION | **reste** (contrat) |
| `config/` + `config.py` + `constants.py` | 559 | CONFIGURATION | → noyau |
| `neron_logging` | 72 | OBSERVABILITY | → noyau |
| `app.py` | 1 253 | LIFECYCLE | **reste** |
| `status.py` | 117 | OBSERVABILITY | **reste**, mais importe `modules.scheduler` |
| `agents/`, `world_model/`, `tools/`, `scheduler/`, `agent_runtime/` | 39 | **LEGACY** | façades `sys.modules[...] = ...` à supprimer |

**Doit sortir de Core** : `goal_engine` (Goal), le corpus identité + config + storage +
infrastructure + governor (noyau partagé), le sandbox d'agents (agents), les 5 façades legacy.

**Reste dans Core** : `app`, `api`, `gateway`, `pipeline`, `orchestration`,
`control_plane`, `a2a`, `modules/self_model`, `status`.

### Les façades legacy

Cinq paquets de Core ne contiennent qu'une réécriture de `sys.modules` :

```python
# server/core/world_model/world_model.py
import sys
from modules.world_model import world_model as _world_model
sys.modules[__name__] = _world_model
```

Elles existent uniquement pour que `core.app` puisse monter des routes dont le code
vit dans le parent. Ce sont le **symptôme visible de la dépendance inversée**, pas
la cause. Elles disparaissent d'elles-mêmes quand le code métier rejoint sa plateforme.

---

## 2. Cartographie des dépendances

**303 sites d'import inter-plateformes.** La Phase 1 estimait ~25 et ~40 sites sur
l'axe Core ↔ parent ; la mesure exacte donne **52 dans chaque sens**, soit le double.

| source \ cible | agents | common | core | goal | integr. | llm | modules | tools | voice |
|---|---|---|---|---|---|---|---|---|---|
| **agents** | · | 7 | **32** | 7 | 2 | 4 | **26** | 4 | 2 |
| **core** | **20** | 10 | · | **26** | 1 | · | **30** | 2 | · |
| **modules** | 4 | 15 | **18** | 15 | · | · | · | 3 | · |
| **tools** | 1 | 4 | 2 | · | 2 | · | 10 | · | · |
| **goal** | 3 | 21 | 2 | · | 2 | · | 3 | · | · |
| **llm** | · | 4 | 2 | · | · | · | · | · | · |
| **integrations** | · | 2 | 1 | · | · | · | · | 1 | · |
| **voice** | 2 | 2 | · | · | · | · | · | · | · |
| doctor / memory / print / reminders / calendars | · | 2-3 | · | · | · | · | · | · | · |

`common` n'a **aucune arête sortante** : c'est le seul puits du graphe.
C'est ce qui en fait la destination sûre du noyau (§5).

---

## 3. Les cycles

Il n'y a pas « quelques cycles » : il y a **une seule composante fortement connexe
de 8 nœuds**.

```
        ┌──────────────────────────────────────────────┐
        │   agents ⇄ core ⇄ modules ⇄ tools            │
        │      ⇅       ⇅       ⇅        ⇅              │
        │    voice    goal   integrations   llm        │
        └──────────────────────────────────────────────┘
                 un seul bloc : 8 nœuds, 28 arêtes internes
```

Acycliques (sains) : `common`, `doctor`, `memory`, `print`, `reminders`, `calendars`.

**12 cycles élémentaires de longueur 2** — les plus lourds :

| Cycle | Sites | Nature |
|---|---|---|
| `agents ⇄ core` | 32 + 20 = **52** | Core monte le runtime d'agents ; les agents consomment le noyau de Core |
| `core ⇄ modules` | 30 + 18 = **48** | Core monte les routes des modules ; les modules consomment le noyau de Core |
| `agents ⇄ modules` | 26 + 4 = **30** | les agents consomment l'Event Bus et code_awareness |
| `core ⇄ goal` | 26 + 2 = **28** | Core importe Goal **en processus** alors que Goal est un service HTTP |
| `goal ⇄ modules` | 3 + 15 = **18** | modules pilotent le planner/task_manager de Goal |
| `modules ⇄ tools` | 3 + 10 = **13** | outils générés ↔ registre d'outils |

**Cause racine, en une phrase :** Core héberge à la fois les **primitives de noyau**
dont tout le monde a besoin (config, auth, identity, governor, storage, normaliseur)
**et** monte les **services métier** qui vivent dans le parent. Chaque plateforme doit
donc traverser Core pour atteindre le noyau, et Core doit traverser le parent pour
servir ses routes.

### Ce que le parent demande à Core (52 sites, par nature)

| Nature | Sites | Modules |
|---|---|---|
| **Noyau** (config, auth, identity, governor, storage, constants, normaliseur, status) | **35** | `core.config` (10), `core.runtime.governor` (8), `core.identity` (5), `core.api.auth` (4), … |
| Agent logic hébergée par Core | 10 | `core.autonomous.*` (7), `core.runtime.sandbox.agent_sandbox` (3) |
| SelfModel | 5 | `core.modules.self_model` |
| Contrats de providers | 4 | `core.providers.{models,registry,protocol}` |
| Rappel d'orchestration | 2 | `core.orchestration.command_dispatcher` |

**35 sites sur 52 (67 %) ne demandent pas « Core » : ils demandent un noyau.**

---

## 4. SelfModel — état réel

### Implémentation

Canonique et unique : `server/core/modules/self_model/` (1 459 lignes, 14 fichiers).
API publique (`__init__.py`) : `SelfModel`, `get_self_model`, `load_self_model_state`,
`build_self_model_snapshot`, `build_self_model_response`, `get_self_model_status`.

### Producteurs

| Producteur | Processus | Fréquence | Écrit |
|---|---|---|---|
| `neron-self-model-loop.service` → `refresh()` + `save_state()` | **processus dédié** | **toutes les 5 s** | fichier complet |
| `core/pipeline/routing/agent_router.py` → `set_last_*`, `add_recent_activity` | **processus Core** | **par requête** | fichier complet |
| `core/pipeline/intent/intent_router.py` → `set_last_intent` | processus Core | par requête | fichier complet |
| `modules/self_model/subscriber.py` → `update_from_event` | processus Core (Event Bus) | par événement | fichier complet |

### Consommateurs

`core/api/self_model_routes.py`, `core/api/cognitive_core_routes.py`,
`core/api/cognitive_report_routes.py`, `core/goal_engine/self_model_client.py`,
`agents/builtin/core/self_model_agent.py`,
`agents/builtin/conversation/conversation_agent.py`,
`modules/self_model/monitor.py`.

### Persistance — le défaut

Un seul fichier : `data/self_model_state.json`, **47 Ko**.
Écriture via `state.py::_write_state` (écriture temporaire + `replace`, donc atomique
au niveau fichier). Mais la mutation passe par :

```python
def _merge_state(self, patch):
    _write_state(_read_state() | patch)     # lecture-modification-écriture, SANS verrou
```

Conséquences mesurées :

1. **Course entre processus.** La boucle (processus dédié) et Core (processus API)
   font tous deux un *read-modify-write* non verrouillé du même fichier. Le dernier
   écrivain gagne : les mises à jour de l'autre sont perdues. `save_state()` de la
   boucle écrase ce que Core vient d'écrire, et réciproquement.
2. **Amplification d'écriture.** Le chemin
   `agent_router.py:694-713` enchaîne **7 `_merge_state` consécutifs** pour une seule
   requête (`set_agents_available`, `set_last_agent`, `set_last_action`,
   `set_last_decision`, `set_last_reasoning`, `add_recent_activity`, `set_last_error`),
   soit ~660 Ko de lecture + écriture **par requête**. La boucle ajoute 47 Ko toutes
   les 5 s, en continu. Sur un disque à 98 %, ce n'est pas neutre.
3. **`refresh()` est un rebuild complet.** `collect_runtime()`, `collect_services()`,
   `compute_health()`, `compute_cognitive_state()` et `compute_runtime_mode()` sont
   **cinq alias de `self.refresh()`**, qui reconstruit tout le snapshot (appels
   `systemctl`, sondes HTTP des services…). `save_state()` appelle `to_dict()` qui
   rappelle `build_self_model_snapshot()`.

### Recommandation

| Axe | Recommandation |
|---|---|
| **Source de vérité** | L'objet en mémoire du **processus Core**. Le fichier JSON n'est qu'un cache de redémarrage, jamais un canal d'échange entre processus. |
| **Producteurs** | Un seul écrivain : Core. Les *snapshots* coûteux (systemd, HTTP) restent périodiques ; les mutations d'événement restent en mémoire. |
| **Consommateurs** | En processus dans Core ; **hors processus via HTTP** (`/selfmodel/*`), jamais en lisant le fichier. |
| **Persistance** | Écriture périodique (≥ 30 s) et à l'arrêt, pas à chaque mutation. Séparer l'état mutable (petit, fréquent) du snapshot (gros, lent). |
| **Transport** | HTTP pour l'Architecte. Le fichier partagé n'est pas un transport. |
| **Responsabilités** | SelfModel = *représenter*. Il ne collecte pas lui-même : les collecteurs (systemd, registry, providers) lui poussent des faits. |

### La question ouverte de la Phase 1, tranchée techniquement

La Phase 1 relevait une contradiction entre la doc (« boucle legacy, désactivée »)
et la réalité (unité active). La mesure Phase 2A donne l'argument technique :
**la boucle et Core s'écrasent mutuellement**. Le choix reste humain (§ Décisions),
mais l'état actuel n'est pas tenable tel quel.

---

## 5. `common.*` / `server.common.*`

Un seul fichier, deux noms de paquet, à cause de
`PYTHONPATH=/etc/neronOS:/etc/neronOS/server`.

| Variante | Sites | Consommateurs |
|---|---|---|
| `server.common.*` | **63** | tous les services sous-modules (goal 21, core 10, calendars/print/reminders/voice/memory/integrations 2 chacun) + `common` lui-même (15) |
| `common.*` | **29** | code du parent : `modules` (15), `agents` (7), `tools` (4) + `doctor` (1), `llm` (1), `common` (1) |

Le clivage recouvre exactement la frontière **code du parent** / **code des sous-modules**.
Le seul module importé sous les deux noms est `common.paths` (29 nus + 25 préfixés).

### Décision : `server.common.*` est canonique

Raisons : majoritaire (63 vs 29) ; c'est ce que `server/common` utilise pour ses
propres imports internes ; c'est ce qu'utilisent tous les services ; le nom est
non ambigu (une seule racine `PYTHONPATH` le résout).

**Exception à conserver** : `common.serve`. Le point d'entrée systemd est
`python -m common.serve <nœud>`, qui exige le nom nu. Changer cela imposerait de
modifier `neron@.service`. À traiter séparément, pas en Phase 2A.

### Risque actuel : contenu, pas nul

Un module chargé sous deux noms produit **deux objets modules distincts**, donc deux
jeux d'état. Inventaire de l'état au niveau module dans `server/common` :

* `metrics.py` — `_PROC`, `_SERVICE_REGISTRY`, 3 gauges → **déjà neutralisé en Phase 1** (registre privé) ;
* `paths.py` — constantes `Path` pures → duplication sans effet ;
* `serve.py` — constante `NERON_ROOT` → sans effet.

Aucun autre singleton. Le danger est donc **latent** : il se réveillera dès qu'un
module porteur d'état (`registry.client`, `service`, `config`) sera importé sous le
nom nu. Deux fichiers de sous-module le font déjà pour `paths` :
`server/doctor/config.py:9` et `server/llm/config.py:11`.

---

## 6. Contrats de Core

### Core ↔ LLM — *existe, correct*

| | |
|---|---|
| Interface | `core.providers.protocol.ProviderProtocol`, implémentée par `ExternalLLMProvider` |
| Entrée | `ProviderRequest(action, payload, trace_id)` — `action ∈ {generate, chat}` |
| Sortie | `ProviderResponse(provider, action, status, result, error, trace_id)` |
| Erreurs | exception réseau → `status="unavailable"` + champ `error` ; jamais de levée vers l'appelant |
| Timeout | `NERON_LLM_TIMEOUT` (défaut 30 s) ; santé plafonnée à 5 s |
| Transport | HTTP `POST {NERON_LLM_URL}/{generate\|chat}`, `Bearer NERON_API_KEY` |
| Responsabilité | Core ne connaît **pas** Ollama. Le choix modèle/provider appartient au service LLM (`tasks:` de `neron.yaml`). Conforme à la cible. |
| Dette | pas d'injection du client HTTP ; un `httpx.AsyncClient` est créé **à chaque appel** (pas de pooling, non testable sans monkeypatch). |

### Core ↔ Memory — *existe, même forme*

Même protocole, `ObliviaProvider`, nom de registre `oblivia-memory`,
actions `remember` / `recall` / `search` / `status`.
Dette identique : `ObliviaProvider()` ne prend plus de chemins → non isolable en test.

### Core ↔ Goal — **contrat violé**

Deux chemins coexistent :

* **contrat** : `core/pipeline/goal_client.py` → HTTP vers `nodes.goal` (127.0.1.3:8030) ;
* **hors contrat** : **26 imports en processus** de `goal.goals.goal_manager`,
  `goal.system.task_manager`, `goal.goals.goal_orchestrator`, `goal.planning.*`…

Goal est un **service séparé avec son propre port**. Core en importe pourtant les
internes, ce qui signifie que le code de Goal s'exécute **aussi** dans le processus
Core, avec son propre état, en parallèle du vrai service. C'est la violation de
contrat la plus grave de l'inventaire.

### Core ↔ SelfModel — *en processus, à formaliser*

Pas de protocole : appel direct `get_self_model()` (singleton par processus).
Contrat cible : lecture seule pour l'Architecte via HTTP `/selfmodel/*` ;
écriture réservée à Core. Voir §4.

### Core ↔ Capabilities — *existe, correct*

`ProviderRegistry` + `ProviderProtocol` + `core.a2a` (AgentCard / AgentMessage / AgentTask).
6 providers par défaut : `llm`, `oblivia-memory`, `homeassistant`, `wikipedia`,
`web-search`, `obsidian-knowledge`. Capacités nommées (`llm.generate`,
`homeassistant.state`…). C'est le point d'entrée correct pour MCP plus tard.

---

## 7. Plan de migration des ~28 000 lignes

Ordre imposé par les cycles. **Aucun déplacement de code métier avant l'étape 3.**

### Étape 1 — Extraire le noyau vers `server/common` *(débloque 35 des 52 sites)*

Déplacer, avec réexport de compatibilité depuis l'ancien emplacement :
`core.config` + `core.config.paths`, `core.constants`, `core.identity`,
`core.api.auth` + `core.infrastructure.auth`, `core.runtime.governor`,
`core.storage.sqlite_store`, `core.pipeline.nlp.french_normalizer`.

Prérequis mesurés : `common` n'importe **aucune** plateforme (verrouillé par
`test_architecture_boundaries.py`). Dépendances internes à emporter :
`config → config.paths + identity`, `governor → infrastructure.event_bus`,
`auth → infrastructure.auth`, `sqlite_store → config.paths`.
`constants` et `french_normalizer` sont des feuilles pures (déplaçables seuls).

**Résultat attendu : `*→core` passe de 57 à 22 sites.** Le cycle survit — c'est normal.

### Étape 2 — Sortir de Core ce qui n'est pas de Core *(traite les 17 restants)*

* `core.autonomous.*` (7 sites) et `core.runtime.sandbox.agent_sandbox` (3) → `agents` ;
* `core.providers.{models,protocol,registry}` (4) → contrats partagés dans `common` ;
* `core.orchestration.command_dispatcher` (2) → inversion : les agents publient un
  événement, Core s'y abonne ;
* `core.modules.self_model` (5) → reste dans Core, exposé par HTTP (§4).

**Résultat attendu : le cycle `agents ⇄ core` et `modules ⇄ core` disparaissent.**

### Étape 3 — Couper `core → goal` en processus

Router les 26 imports vers `core/pipeline/goal_client.py` (HTTP). C'est la
correction de contrat la plus lourde, mais elle supprime un doublon d'exécution.

### Étape 4 — Alors seulement, déplacer le code métier

Dans cet ordre, plateforme par plateforme, en s'appuyant sur le cliquet :

1. `modules/capabilities`, `modules/context`, `modules/sessions`, `modules/personality`, `modules/events`, `modules/service_core` → **Core** ;
2. `modules/cognitive`, `modules/cognitive_core`, `modules/evolution`, `modules/self_repair`, `modules/autonomous`, `modules/validation`, `modules/scheduler`, `modules/code_awareness`, `tools/` → **Goal** ;
3. `agents/builtin/{communication,io}`, `agents/searchx`, `integrations/homeassistant` → **Capabilities** ;
4. `agents/factory`, `agents/runtime`, `agents/autonomous` → **Goal** (l'usine) ;
5. `core/goal_engine` (1 740 lignes) → **Goal** ;
6. `modules/memory` → **Memory** ; `modules/world_model` → gelé.

### Étape 5 — Supprimer les 5 façades `sys.modules`

Elles n'ont plus d'objet une fois l'étape 4 terminée.

### Comment ne rien casser

* Le cliquet `tests/test_architecture_boundaries.py` échoue à la moindre arête qui monte.
* Chaque déplacement passe par un réexport de compatibilité, supprimé une fois les appelants migrés.
* Les services tournent en processus séparés : une plateforme peut être migrée sans redémarrer les autres.
* `./system/deploy/install.sh check` et `make health` valident l'état déployé après chaque étape.
