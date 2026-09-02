# NéronOS — Architecture de référence

Statut : **référence courante**
Établi en Phase 1 (consolidation du dépôt parent), 31/08/2026.

Ce document fait foi. Toute documentation qui le contredit est historique et
doit être corrigée ou archivée.

---

## 1. Les quatre blocs

```
                        ┌──────────────────────────┐
                        │          CŒUR            │
                        │   comprendre, raisonner, │
                        │   générer, mémoriser     │
                        │                          │
                        │       LLM  ·  Memory     │
                        └────────────┬─────────────┘
                                     │
                            ┌────────▼────────┐
                            │    SELFMODEL    │   pont d'état
                            │  identité, état,│
                            │  capacités,     │
                            │  santé, versions│
                            └────────┬────────┘
                                     │
                        ┌────────────▼─────────────┐
                        │        ARCHITECTE        │
                        │                          │
                        │  Watchdog → constate     │
                        │  Doctor   → analyse      │
                        │  Goal     → répare/évolue│
                        └──────────────────────────┘

        ┌──────────────────────────────────────────────────┐
        │            CAPABILITIES / SERVICES               │
        │  MCP · Home Assistant · GitHub · Notion · Web    │
        │  fichiers · impression · agenda · rappels · …    │
        └──────────────────────────────────────────────────┘
```

**Cœur** — LLM, Memory.
**Architecte** — Goal (l'usine : crée et gère agents et outils, planifie,
répare, fait évoluer, avec validation humaine sur les évolutions sensibles),
Doctor, Watchdog.
**SelfModel** — interface d'état entre le Cœur et l'Architecte. Ce n'est pas un
cerveau supplémentaire : il représente Néron, il ne raisonne pas à sa place.
**Capabilities / Services** — capacités externes. Les connecteurs MCP
appartiennent ici, jamais au Core, au LLM, à Memory ou à Goal.

**WorldModel** — hors priorité. Voir §7.

---

## 2. Rôle du dépôt parent

`neronOS` est l'ossature. Il porte :

* l'organisation globale et les sous-modules ;
* la configuration globale (`neron.yaml`, `neron.server.yaml`, `env/common.env`) ;
* le déploiement et l'orchestration système (`system/deploy`) ;
* les scripts d'exploitation (`system/scripts`) ;
* le socle partagé (`server/common`) ;
* la documentation et les tests de contrat.

Il ne doit **pas** porter la logique métier des sous-modules. Ce n'est pas
encore vrai aujourd'hui : voir §6.

---

## 3. Cartographie du dépôt

| Chemin | Propriétaire | Classement | Statut |
|---|---|---|---|
| `server/core` | Core | CORE | sous-module |
| `server/llm` | Cœur | LLM | sous-module |
| `server/memory` | Cœur | MEMORY | sous-module |
| `server/goal` | Architecte | GOAL | sous-module |
| `server/doctor` | Architecte | DOCTOR | sous-module |
| `server/watchdog` | Architecte | WATCHDOG | sous-module **vide (v0.0.0)** |
| `server/voice` | Capabilities | CAPABILITIES | sous-module |
| `server/print` | Capabilities | CAPABILITIES | sous-module |
| `server/reminders` | Capabilities | CAPABILITIES | sous-module |
| `server/calendars` | Capabilities | CAPABILITIES | sous-module |
| `server/common` | Parent | SYSTEM | socle partagé — légitime dans le parent |
| `server/modules` | **à répartir** | CORE/GOAL/SELF-MODEL | ~12 k lignes dans le parent (§6) |
| `server/agents` | **à répartir** | CORE/GOAL/CAPABILITIES | ~11 k lignes dans le parent (§6) |
| `server/tools` | **à répartir** | GOAL | ~3 k lignes dans le parent (§6) |
| `server/integrations` | Capabilities | CAPABILITIES | Home Assistant, dans le parent |
| `client/client` | Interface | — | sous-module (mobile Next.js) |
| `client/dashboard` | Interface | — | sous-module |
| `client/neronVoice` | Interface | — | sous-module |
| `neron.yaml` | Parent | CONFIG | comportement fonctionnel |
| `neron.server.yaml` | Parent | CONFIG | topologie (`nodes`) — source de vérité |
| `env/common.env` | Parent | CONFIG | environnement d'exécution commun |
| `secrets.env` | Parent | CONFIG | secrets, **non versionné**, mode 0640 |
| `system/deploy` | Parent | SYSTEM | unités systemd, Caddy, installateur |
| `system/scripts` | Parent | SYSTEM | exploitation |
| `system/requirements` | Parent | CONFIG | dépendances |
| `system/docs` | Parent | DOCUMENTATION | ce document |
| `tests` | Parent | TEST | tests de contrat du parent |
| `tools` | Parent | SYSTEM | outillage ponctuel |

---

## 4. Topologie et démarrage

La topologie vit **uniquement** dans `neron.server.yaml`, section `nodes`.
Aucun port n'est codé en dur dans une unité systemd.

Tous les services métier passent par un template unique :

```
neron@<noeud>.service
  └── /etc/neronOS/venv/bin/python -m common.serve <noeud>
        └── lit nodes.<noeud> dans neron.server.yaml
        └── importe <noeud>.app:app
        └── uvicorn
```

`neron.target` doit lister tous les nœuds activés sur l'hôte. Un service absent
de `neron.target` n'est pas démarré par `systemctl start neron.target`, même
s'il est `enable`.

Unités autonomes (hors template) :

| Unité | Lance | Bloc |
|---|---|---|
| `neron-cognitive-loop.service` | `modules.autonomous.run_cognitive_loop` | Architecte |
| `neron-self-model-loop.service` | `modules.self_model.self_model_loop` | SelfModel |
| `neron-world-model-loop.service` | `modules.world_model.world_model_loop` | WorldModel (§7) |
| `neron-homeassistant-registry.service` | `integrations.homeassistant.registry_runner` | Capabilities |
| `neron-doctor-diagnose.{service,timer}` | `system/scripts/doctor_diagnose.sh` | Architecte |
| `neron-relecture.{service,timer}` | `tools/relecture_nuit.sh` | Cœur (Memory) |
| `neron-client`, `neron-dashboard`, `neron-voice-interface` | front pnpm | Interface |

Toute unité déployée doit être versionnée dans `system/deploy/systemd/`.
`./system/deploy/install.sh check` compare dépôt et système ;
`sudo make install` applique.

---

## 5. Contrats inter-plateformes

Contrats constatés en Phase 1. Ils décrivent l'existant, pas une cible.

| Contrat | Entrée | Sortie | Responsabilité | Transport |
|---|---|---|---|---|
| Core → LLM | tâche + prompt (`task_type`) | complétion | router modèle/provider selon `tasks:` de `neron.yaml` | HTTP `nodes.llm` `/llm` |
| Core → Memory | requête sémantique, écriture de fiche | rappels, fiches | source de vérité des connaissances (Oblivia) | HTTP `nodes.memory` |
| Core → Goal | intention / commande d'évolution | plan, tâches, projets | planifier et exécuter l'évolution | HTTP `nodes.goal`, `core/pipeline/goal_client.py` |
| Goal → Doctor | demande de diagnostic | rapport de santé | analyser | HTTP `nodes.doctor`, clé `X-Doctor-Key` |
| Goal → Watchdog | — | constats | **non implémenté** (§6) | — |
| Core → SelfModel | événements du bus, snapshots | état consolidé | représenter Néron | **in-process** `core.modules.self_model` |
| Architecte → SelfModel | lecture d'état | capacités, providers, agents, architecture | lecture seule | in-process + `/self-model` |
| Capabilities → Core | enregistrement au registry | présence, capacités | s'annoncer | `server/common/registry` → Core |

**Registry.** Chaque service construit avec `server/common/service.py`
(`create_service_app`) s'annonce au Core au démarrage et se réannonce
périodiquement. Le Core n'utilise pas ce squelette (décision du 01/08).

**SelfModel canonique.** L'implémentation vit dans le sous-module Core :
`server/core/modules/self_model/service.py`. Le parent ne fournit que des
pilotes (`server/modules/self_model/` : boucle, abonné, moniteur).
Ne pas créer de second SelfModel.

---

## 6. Dette structurelle connue

### 6.1 Couplage circulaire parent ↔ sous-modules

C'est le point dur de l'architecture actuelle.

```
server/core, server/goal, server/voice   ──importent──▶  modules.*, agents.*, tools.*
server/modules, server/agents, server/tools ──importent──▶  core.*, goal.*, llm
```

> **Mesuré en Phase 2A** : l'estimation ci-dessous était basse d'un facteur 2.
> Le compte exact est de **52 sites dans chaque sens**, sur **303 sites d'import
> inter-plateformes** au total, formant **une seule composante fortement connexe
> de 8 nœuds**. Détail, cycles et plan de migration :
> [phase2a-core-decoupling.md](phase2a-core-decoupling.md).

Conséquences : le Core ne peut pas être audité isolément, le parent ne peut pas
évoluer sans casser un sous-module, et les tests du parent sondent des internes
de sous-module.

La cible reste :

```
Parent ──▶ interfaces / contrats ──▶ sous-modules
```

Résorption prévue en Phase 2 (Core) puis Phase 3 (LLM).

### 6.2 Code métier hébergé par le parent

`server/modules` (~12 k lignes), `server/agents` (~11 k), `server/tools` (~3 k)
sont exécutés en production mais n'appartiennent architecturalement pas au
parent. Répartition cible indicative :

| Paquet du parent | Destination |
|---|---|
| `modules/capabilities`, `modules/context`, `modules/sessions`, `modules/personality`, `modules/events`, `modules/service_core` | Core |
| `modules/cognitive`, `modules/cognitive_core`, `modules/evolution`, `modules/self_repair`, `modules/autonomous`, `modules/validation`, `modules/scheduler`, `modules/code_awareness`, `tools/` | Goal |
| `modules/self_model` | pilotes du SelfModel (Core) |
| `modules/world_model` | WorldModel — gelé (§7) |
| `modules/memory` | Memory |
| `agents/builtin/{communication,io}`, `agents/searchx`, `integrations/homeassistant` | Capabilities / Services |
| `agents/factory`, `agents/runtime`, `agents/autonomous` | Goal (l'usine) |

Ne rien déplacer avant d'avoir traité 6.1 : déplacer du code qui importe encore
en cercle ne ferait que déplacer le problème.

### 6.3 Double nom de paquet pour `server/common`

`PYTHONPATH=/etc/neronOS:/etc/neronOS/server` rend `server/common` importable
sous deux noms : `common.x` et `server.common.x`. Les deux conventions coexistent
(`common.paths` d'un côté, `server.common.service` de l'autre) et Python charge
alors deux modules distincts pour un même fichier. C'est ce qui faisait échouer
l'enregistrement des métriques Prometheus (corrigé côté parent par un registre
privé dans `server/common/metrics.py`). Unifier sur un seul nom en Phase 2.

### 6.4 Watchdog inexistant

`server/watchdog` est un sous-module vide (`VERSION` = `v0.0.0`, aucun code).
`neron@watchdog.service` n'est ni activé ni démarré, alors que
`neron.server.yaml` déclare un nœud `watchdog` (127.0.1.6:8003). Le maillon
« constate » de l'Architecte n'existe donc pas.

### 6.5 CORS et `server_override`

`neron.yaml` déclare `config.server_override: neron.server.yaml`, mais aucun
chargeur n'implémente cette fusion. `server/core/config.py` lit `server:`
directement dans `neron.yaml`. La section `server:` de `neron.server.yaml` a été
retirée en Phase 1 : elle était inerte et divergeait de la version active.

### 6.6 Tests neutralisés

Huit modules de `tests/` sondent des API de sous-module supprimées ou renommées.
Ils sont conservés, mais neutralisés par un `pytest.skip` de niveau module afin
que la suite du parent reste collectable. À réparer en Phase 2/3 :

`test_builder`, `test_dynamic_predicate_discovery`, `test_goal_v2_provider_memory_api`,
`test_identity_loader`, `test_memory_ontology`, `test_oblivia_normalization`,
`test_providers_a2a`, `test_selfmodel_system_api`.

---

## 7. WorldModel

Le WorldModel **existe déjà** et tourne :

* implémentation : `server/modules/world_model/world_model.py` ;
* façade dans le Core : `server/core/world_model/`, `core/api/world_model_routes.py` ;
* boucle : `neron-world-model-loop.service`, active.

Il est **hors priorité**. Ne pas l'étendre. Décision à prendre par un humain :
le geler tel quel, ou l'arrêter en attendant une reprise ultérieure.

---

## 8. MCP

Aucun connecteur MCP n'existe aujourd'hui dans le dépôt : zéro occurrence dans
le parent. Rien n'est donc mal placé. Quand MCP arrivera, il devra être créé
sous **Capabilities / Services**, et non dans Core, LLM, Memory ou Goal.

---

## 9. Phases

| Phase | Périmètre | État |
|---|---|---|
| 1 | Consolidation du dépôt parent | faite |
| 2A | Audit et découplage de `core` : cartographie, cycles, contrats, cliquet | faite |
| 2B | SelfModel à écrivain unique, identité configurable, Runtime Governor extrait vers le noyau | partielle |
| 2C | Reste du noyau (identity/config/auth/storage), puis Core → Goal en HTTP | à venir |
| 3 | Audit et blindage de `llm` (puis `memory`) | à venir |
| 4 | Watchdog réel, puis Goal en usine complète | à venir |
| — | WorldModel | gelé |
