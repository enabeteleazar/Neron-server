# Chantier 2 - Audit et nettoyage des doublons

Date: 12 juin 2026

## Résumé exécutif

La Phase 2 a confirmé que la principale duplication de décision avait déjà été
traitée en Phase 1. Le nettoyage a donc porté sur les chemins morts, les
surfaces legacy, les implémentations techniques incomplètement raccordées et
les copies de déploiement strictement identiques.

Résultat:

- une seule implémentation active de `POST /input/text`;
- suppression de `_legacy_text_input`;
- suppression du planificateur NLP historique sans appel;
- suppression d'un agent Self Model local sans import;
- retrait du chat OpenAI dormant du dashboard;
- fusion des générations Tool Creator v1 et v2 derrière `ToolCreator`;
- dépréciation explicite des routes legacy de tâches et de l'exécution directe
  du planner;
- suppression de cinq copies systemd byte-identiques;
- aucune donnée JSON/SQLite, aucun agent généré et aucun registry supprimé;
- 495 tests passent;
- dashboard compilé;
- `neron-core` redémarré et actif.

## Méthode d'audit

Les doublons ont été recherchés par:

- inventaire des fichiers et répertoires;
- recherche des imports, appels, montages FastAPI et usages UI;
- comparaison SHA-256 des unités systemd;
- inspection des routes OpenAPI et recherche de couples méthode/chemin
  enregistrés plusieurs fois;
- inventaire en lecture seule des stores JSON, JSONL et SQLite;
- tests ciblés puis suite complète.

La suppression n'a été appliquée que lorsqu'aucun appel n'était trouvé ou
qu'une surface canonique était déjà prouvée par le runtime et les tests.

## Doublons identifiés et classification

| Domaine | Doublon ou chevauchement | Risque | Décision |
|---|---|---:|---|
| Input/routage | `_legacy_text_input` versus `CoreOrchestrator.handle` | Faible | Ancien handler supprimé |
| Input/routage | `core.gateway.http_gateway` expose aussi `/input/text` et `/input/stream` | Moyen | Conservé: router non monté dans `core.app`, mais initialisé par le Control Plane |
| Intent | `IntentRouter`, `AgentRouter`, Capability Resolver et CoreOrchestrator | Moyen | Conservés comme classifieur/exécuteurs; aucune autorité concurrente réintroduite |
| NLP | `orchestrator_plan.py` sans import ni appel | Faible | Supprimé |
| Planner | `/planner/execute/{id}` et `/planner/execute-approved/{id}` | Élevé | Exécution directe marquée deprecated; route approuvée conservée |
| Tasks | routes `/tasks/legacy*` et routes modernes | Moyen | Routes legacy conservées mais marquées deprecated |
| Goals | `core.goal_system.GoalSystem` et `core.goals.GoalManager` | Élevé | Non fusionnés: deux formats persistants et usages cognitifs actifs |
| Plans/tasks | Planner, GoalOrchestrator, TaskManager et ProjectManager | Élevé | Non fusionnés: responsabilités liées mais contrats persistants distincts |
| Tools | Tool Creator v1 spécialisé logs et v2 générique incomplet | Moyen | Fusionnés derrière `ToolCreator`; chaîne logs canonique préservée |
| Tools runtime | `core.runtime.tools.ToolManager` et `core.tools.ToolRuntime` | Moyen | Non supprimé: ancien manager sans import interne, mais surface runtime potentiellement externe |
| Agents | `core.agents.self_model_agent` et `core.agents.core.self_model_agent` | Faible | Ancienne variante sans import supprimée |
| Agents | workspace, generated, registry et runtime | Élevé | Conservés: workspace = brouillon, generated = promotion, registry = index, runtime = exécution |
| Registry agents | `core.runtime.agents.AgentRegistry` et `DynamicAgentRegistry` | Moyen | Conservés; le premier est non référencé en interne mais appartient à une surface runtime |
| World Model | `core.memory.world_model` et `core.world_model` | Élevé | Conservés: legacy enrichi encore utilisé par watchdog/tests, officiel utilisé par l'API |
| Self Model | deux agents de présentation | Faible | Variante morte supprimée; modèle officiel conservé |
| Memory | SQLite conversationnelle, Obsidian, learning/reasoning memory | Élevé | Conservés: finalités et stores distincts |
| Santé | HealthManager, watchdog, SelfModel health et Doctor | Élevé | Conservés: métriques, détection, synthèse cognitive et remédiation sont complémentaires |
| Dashboard | routeur chat OpenAI Replit versus `/input/text` Core | Faible | Routeur OpenAI et contrat `/api/chat` dormants supprimés |
| Dashboard | intégrations audio/image OpenAI Replit non montées | Moyen | Conservées et documentées; hors nettoyage chat demandé |
| API | routes parallèles FastAPI | Moyen | Aucun couple méthode/chemin dupliqué dans les 114 chemins OpenAPI |
| Systemd | copies identiques dans `deploy/` et `deploy/systemd/` | Faible | Cinq copies secondaires supprimées |
| Systemd | deux unités Home Assistant divergentes | Élevé | Non modifiées; utilisateurs, chemins et politiques de restart différents |
| Systemd | `deploy/systemd/neron.service` legacy | Moyen | Conservé: statut legacy explicitement testé |
| Données | JSON + SQLite pour goals/tasks/projects | Élevé | Inventoriés seulement; aucune migration ou suppression |
| Tests | suites Tool Creator v1 et v2 | Faible | Conservées: elles couvrent compatibilité logs et génération générique |

## Actions appliquées

### Routage et API

- suppression complète de `_legacy_text_input`;
- maintien de `POST /input/text` sur `CoreOrchestrator`;
- suppression de `core/pipeline/nlp/orchestrator_plan.py`;
- marquage OpenAPI `deprecated` de `POST /planner/execute/{plan_id}`;
- marquage OpenAPI `deprecated` de toutes les routes `/tasks/legacy*`;
- vérification qu'aucune méthode HTTP n'est enregistrée deux fois sur le même
  chemin.

### Tool Creator

- ajout du contrat `ToolNeed` dans les modèles existants;
- raccordement du builder de specs et des générateurs déterministe/Codex;
- génération, validation AST, chargement runtime et réutilisation depuis le
  registry;
- ajout de `POST /tools/plan` et `POST /tools/create-from-need`;
- préservation de la chaîne spécialisée logs:
  `neron_log_reader_tool`, `neron_log_error_filter_tool`,
  `neron_log_summary_tool`;
- correction de `test_tool_creator_v2.py`, qui échouait auparavant à la
  collecte faute de `ToolNeed`.

### Dashboard

- suppression du routeur OpenAI direct
  `server/replit_integrations/chat/routes.ts`;
- suppression de son export;
- suppression du contrat partagé `/api/chat`;
- conservation de `chat/storage.ts`, encore importé par l'intégration audio
  dormante;
- aucune suppression de la dépendance `openai`, encore utilisée par les
  intégrations audio/image.

### Self Model et systemd

- suppression de `core/agents/self_model_agent.py`, sans import et explicitement
  remplacé par `core.agents.core.self_model_agent`;
- suppression des copies identiques suivantes:
  - `deploy/systemd/neron-cognitive-loop.service`
  - `deploy/systemd/neron-core.service`
  - `deploy/systemd/neron-doctor.service`
  - `deploy/systemd/neron-llm.service`
  - `deploy/systemd/neron-stt.service`

L'installateur utilise `deploy/`, pas `deploy/systemd/`.

## Actions non appliquées

- aucune suppression de JSON, JSONL, SQLite ou historique;
- aucune suppression dans `workspace/agents` ou `core/agents/generated`;
- aucune suppression de registry persistant;
- aucune fusion destructive de GoalSystem/GoalManager;
- aucune suppression du World Model legacy encore utilisé par watchdog;
- aucune suppression du Doctor, du Health Center ou des services actifs;
- aucune suppression de `core.gateway.http_gateway`, car le Control Plane
  initialise encore cette surface;
- aucune suppression des anciens registries/managers runtime sans preuve
  d'absence d'appel externe;
- aucune création d'objectif de validation persistant.

## Raisons des décisions

Les répertoires workspace et generated contiennent plusieurs fichiers
byte-identiques. Il ne s'agit pas de doublons supprimables: le premier est la
zone de construction/test, le second la zone promue et chargée par le runtime.

GoalSystem et GoalManager se chevauchent fonctionnellement, mais utilisent
encore des formats et consommateurs différents. Une fusion en Phase 2 aurait
impliqué une migration de données et un changement de contrat public.

Health Center, watchdog, Self Model et Doctor produisent tous des informations
de santé, mais à des niveaux différents. Doctor est aussi un service de
diagnostic/remédiation séparé. Leur convergence exige d'abord un contrat de
health commun.

## Risques restants

### Risque élevé

- coexistence de `goals.json`, `goals_state.json` et `neron_state.sqlite3`;
- coexistence du World Model legacy et officiel;
- unités Home Assistant divergentes;
- stores historiques volumineux:
  `action_history.jsonl` environ 622 Mo et `critic_history.jsonl` environ
  394 Mo;
- multiplication des représentations Goal/Plan/Task/Project;
- quatre états d'un agent: workspace, generated, registry, runtime.

### Risque moyen

- ancien `http_gateway` non monté mais encore initialisé;
- `core.runtime.tools.ToolManager` et
  `core.runtime.agents.AgentRegistry` sans appel interne prouvé;
- intégrations Replit audio/image dormantes dans le dashboard;
- erreurs `tsc` préexistantes dans audio, image, batch et le stockage chat
  historique. La compilation de production réussit.

## Fichiers modifiés par la Phase 2

- `core/app.py`
- `core/capabilities/resolver.py`
- `core/tools/models.py`
- `core/tools/creator.py`
- `core/tools/runtime.py`
- `core/tools/routes.py`
- `core/tools/code_generator.py`
- `core/tools/spec_builder.py`
- `core/tools/templates.py`
- `core/api/planner_routes.py`
- `core/api/task_routes.py`
- `core/agents/self_model_agent.py` (supprimé)
- `core/pipeline/nlp/orchestrator_plan.py` (supprimé)
- cinq unités sous `deploy/systemd/` (supprimées)
- sous-dépôt `ui_dashboard`:
  `chat/index.ts`, `chat/routes.ts` et `shared/routes.ts`
- `tests/test_tool_creator_v2.py`
- ce rapport.

Les autres modifications visibles dans le worktree appartenaient déjà à la
Phase 1 et ont été préservées.

## Tests et validations

### Tests

- `pytest -q`: **495 passed**, 3 warnings;
- Tool Creator v2 ciblé: **13 passed**;
- tools/capabilities: **63 passed**;
- autorité orchestrateur/API: **67 passed**;
- goals/runtime: **38 passed**;
- agent factory/registry/workspace: **103 passed**;
- systemd/runtime surface/Tool Creator v2: **18 passed**.

Warnings restants:

- API legacy `websockets.server.WebSocketServerProtocol`;
- package `websockets.legacy`;
- `AgentFactoryAgent` explicitement deprecated.

### Qualité et compilation

- `git diff --check`: OK;
- `git -C ui_dashboard diff --check`: OK;
- `python -m compileall -q core`: OK;
- `npm run build` dans `ui_dashboard`: OK;
- `npm run check`: échec sur erreurs TypeScript préexistantes des intégrations
  Replit audio/image/batch et du schéma chat historique.

### Service

- `neron-core` redémarré le 12 juin 2026 à 14:20:14 CEST;
- état final: `active (running)`;
- startup FastAPI, Gateway WebSocket, Telegram, STT et agents terminée;
- aucun échec de démarrage dans le journal récent;
- un warning `resource_tracker` sur un sémaphore est apparu à l'arrêt de
  l'ancien processus, sans impact sur le redémarrage.

### Endpoints critiques

- `GET /health`: OK, `healthy`;
- `GET /self-model/status`: OK;
- `GET /world-model/status`: OK;
- `GET /planner/status`: OK, planner `available`;
- `GET /goals/active`: OK;
- `GET /projects`: OK, 36 projets;
- `GET /runtime/governor/policy`: OK;
- `POST /input/text`: OK, demande d'heure routée vers `timer_engine`;
- `POST /goal`: contrat validé en 422 avec objectif vide, sans créer de donnée
  persistante. Le chemin nominal est couvert par les tests goals/orchestrateur.

## Résultat avant/après

Avant:

- ancien handler `/input/text` conservé en parallèle dans le code;
- planificateur NLP sans appel;
- deux agents Self Model de présentation;
- chat dashboard capable de contourner Néron Core vers OpenAI;
- Tool Creator v2 non collectable;
- routes legacy non signalées dans OpenAPI;
- cinq manifestes systemd identiques.

Après:

- un seul handler applicatif `/input/text`;
- code NLP mort supprimé;
- un seul agent Self Model importable;
- dashboard chat aligné sur Néron Core;
- Tool Creator v1/v2 unifié et testé;
- routes legacy visibles comme deprecated;
- manifestes systemd canoniques dans `deploy/`;
- aucune donnée utilisateur supprimée.

## Phase 3 recommandée

1. Définir un schéma canonique Goal/Plan/Task/Project et un plan de migration
   non destructif, avec lecture parallèle et rollback.
2. Définir un contrat unique d'état agent couvrant draft, promoted,
   registered et running, puis ajouter un endpoint de réconciliation en lecture
   seule.
3. Choisir le World Model officiel après comparaison des données réellement
   consommées par watchdog et API.
4. Unifier le contrat Health sans fusionner prématurément les responsabilités
   Doctor/watchdog/SelfModel.
5. Décider quelle unité Home Assistant est canonique avant toute suppression.
6. Ajouter rotation/rétention aux historiques JSONL volumineux.
7. Supprimer ou réhabiliter les intégrations Replit audio/image après décision
   produit, puis rendre `npm run check` vert.

La prochaine action recommandée est le point 1: cartographier les champs et
consommateurs des stores Goal/Plan/Task/Project, sans migration destructive.
