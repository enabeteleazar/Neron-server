# Phase 3E - Elimination des couches legacy

Date : 13 juin 2026

## Resultat

Les chemins canoniques sont maintenant :

- promotion d'agent : `core.agent_factory.promotion.AgentPromotionService`
- registre d'agents : `core.agent_factory.registry.DynamicAgentRegistry`
- runtime d'agents : `core.agent_runtime.runtime.AgentRuntime`
- registre d'outils : `core.tools.registry.ToolRegistry`
- runtime d'outils : `core.tools.runtime.ToolRuntime`
- bus d'evenements : `core.events.event_bus.EventBus`
- objectifs et taches : `GoalManager` et `TaskManager`

Les routes publiques existantes sont conservees. Leur implementation utilise les
composants canoniques ci-dessus.

## Cartographie et preuves d'usage

| Composant legacy | Appelants avant nettoyage | Tests / API | Decision |
| --- | --- | --- | --- |
| `AgentRuntimeManager` | build orchestrator, agent manager, routeur, routes projets | tests agents et routes `/agents` | Appelants migres vers `AgentRuntime`, composant supprime |
| `AgentRegistryScanner` | routeur texte et routes `/agents/registry/*` | tests registry et routes | Fonctions integrees a `DynamicAgentRegistry`, composant et index secondaire supprimes |
| `core.runtime.agents.AgentRegistry` | aucun | aucun | Supprime |
| `ToolManager` | seulement `register_default_tools` | aucune route active, aucun test appelant | Supprime avec l'ancien registre runtime |
| `JournalTool` runtime | seulement `register_default_tools` | aucune route active | Supprime; aucun outil canonique ne le declarait |
| `promote_agent` | agent manager, routeur et routes projets | tests de promotion | Appelants migres vers `AgentPromotionService`, fonction supprimee |
| copie directe `_register_agent` | build orchestrator | tests du pipeline | Supprimee; promotion centralisee dans `AgentPromotionService` |
| `AgentFactoryAgent` | aucun appelant applicatif | deux tests de compatibilite, aucune route | Tests adaptes au chemin canonique, facade supprimee |
| `GoalSystem` | aucun | aucune route, aucun test | Supprime; `GoalManager` reste la source de verite |
| `TaskStore` | export de package uniquement | aucun appelant | Supprime; `TaskManager` reste la source de verite |
| `core.runtime.events.*` | references internes au sous-package uniquement | routeur `/events` non monte dans FastAPI | Sous-systeme supprime; publication et persistance restent canoniques |
| packages `runtime.*` | aucun, fichiers `__init__.py` vides | aucun | Supprimes |
| packages vides `core.runtime.agents/tools` | aucun apres migration | aucun | Supprimes |
| helper `_get_agent_factory` | aucun | un test verifiait deja son absence du flux | Supprime |

La recherche finale ne trouve plus les symboles `AgentRuntimeManager`,
`AgentRegistryScanner`, `ToolManager`, `promote_agent` ou
`get_agent_runtime_manager` dans le code applicatif.

## Composants conserves

| Composant | Raison |
| --- | --- |
| `DynamicAgentRegistry` | registre canonique impose par la phase |
| `AgentRuntime` | runtime canonique impose par la phase |
| `ToolRegistry` et `ToolRuntime` | registre et runtime canoniques imposes par la phase |
| `GoalManager` et `ProjectManager` | sources de verite imposees par la phase |
| `core.events.EventBus` | Event Bus canonique |
| `core.control_plane.events.EventBus` | encore instancie par `NeronCore`; adaptateur actif vers le bus canonique |
| wrappers `modules.*` | contrat d'import explicitement couvert par `test_legacy_modules_compat.py` |
| `core.modules.autonomous.scheduler` | utilise par les agents autonomes |
| adaptateur World Model historique | import et exclusion de route explicitement testes |
| routes `/tasks/legacy/*` | API publique marquee deprecated mais encore enregistree |
| route planner d'execution directe | API publique marquee deprecated mais encore enregistree |
| migrations JSON legacy Goal/Plan/Task/Project | necessaires a la reprise des donnees historiques |
| fallback de configuration legacy | encore actif pour les installations existantes |
| fallback legacy du capability resolver | encore execute lorsque la resolution principale ne conclut pas |

## API et stockage

- Aucune route publique critique n'a ete supprimee.
- Les routes `/agents`, `/agents/registry/*` et les routes de promotion utilisent
  desormais les composants canoniques.
- Aucun fichier de donnees ni historique de projet n'a ete supprime.
- Les imports de donnees legacy restent en lecture ou en miroir la ou les tests
  de migration les exigent.
- L'ancien `agent_registry_index.json` n'est plus une source de verite. L'index
  est calcule depuis `DynamicAgentRegistry`.

## Gains

- un seul service de promotion
- un seul runtime d'agents
- un seul registre d'agents
- un seul registre et un seul runtime d'outils
- un seul Event Bus actif
- suppression de plus de 600 lignes de facades, wrappers et registries dupliques
- diagnostics registry calcules depuis la source canonique
- test d'architecture empechant la reintroduction des principaux modules retires

## Dette restante

La dette conservee est volontaire et observable :

- contrats d'import `modules.*`
- adaptateur actif du control plane vers l'Event Bus canonique
- anciennes routes Task et Planner marquees deprecated
- adaptateur d'import World Model
- migrations et miroirs de stockage legacy
- fallback du capability resolver
- alias et champs de reponse historiques encore exposes par certaines API

Leur suppression exige une decision de rupture d'API ou une migration de donnees,
hors du perimetre autorise de cette phase.

## Validation

Commandes executees :

- tests runtime et registry : `15 passed`
- tests tools : `25 passed`
- tests pipeline agents : `16 passed`
- tests agents suivis apres nettoyage final : `91 passed`
- validation de chaque fichier de test dans un processus isole : `521 passed`
- `pytest -q` : `521 passed, 2 warnings`
- `python -m compileall -q core tests` : succes
- `git diff --check` : succes
- `neron-core.service` : actif apres redemarrage
- `GET /health` : `{"status":"healthy","version":"0.1"}`

Les deux avertissements restants concernent l'API `websockets.legacy` et ne sont
pas lies aux couches supprimees.
