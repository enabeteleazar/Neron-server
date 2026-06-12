# Chantier 1 - Autorite de decision unique

Date: 2026-06-12

## Perimetre

Ce chantier porte sur les entrees conversationnelles et les commandes Goal.
Les routes d'administration explicites (`/planner/*`, `/tasks/*`,
`/evolution/*`, `/agents/*`) restent des API specialisees.

## Flux reel avant

| Entree | Premier composant | Decision | Execution | Reponse |
| --- | --- | --- | --- | --- |
| `POST /input/text` | `core.app.text_input` | `core.app`, IntentRouter, Resolver, AgentRouter | agent, LLM, Resolver ou builder | `CoreResponse` |
| `POST /input/stream` | `core.app.text_input_stream` | IntentRouter puis branches locales | LLM ou handlers locaux | SSE |
| `POST /input/audio` | STT | delegation a `/input/text` | pipeline texte | `CoreResponse` |
| `POST /input/voice` | STT | delegation a `/input/text` | pipeline texte puis TTS | audio ou `CoreResponse` |
| Telegram texte | `telegram_agent.handle_message` | evolution locale puis `/input/text` | dispatcher evolution ou Core | message Telegram |
| Telegram `/goal` | `NeronCommandDispatcher` | dispatcher | `GoalOrchestrator` | messages Telegram |
| `POST /goal` | route Goals | route directe | Goal background runner | accusé 202 |
| `POST /goals/run` | route Goals | route directe | `GoalOrchestrator` | resultat Goal |
| WebSocket `chat.send` | `NeronGateway` | AgentRouter | flux LLM/agent | events WebSocket |
| Internal HTTP/WS gateway | `InternalGateway` | AgentRouter | flux LLM/agent | texte/SSE |
| Dashboard actif | proxy `/api/neron/*` | Core appele | `/input/text` ou `/goal` | JSON Core |
| UI vocale | proxy `/api/core` | Core appele | `/input/text` | JSON Core |

Le module dashboard `replit_integrations/chat/routes.ts` contient une route
directe OpenAI, mais aucun enregistrement runtime de `registerChatRoutes` n'a
ete trouve.

## Decideurs concurrents avant

Nombre de niveaux de decision sur le chemin conversationnel principal: 5.

1. `core/app.py::text_input`: grand arbre de routage et appels directs.
2. `IntentRouter`: classification NLP plus surcharge par mots-cles.
3. `CapabilityResolver`: choix outil, agent, creation ou rejet.
4. `AgentRouter`: nouvelle selection d'agent et anciens detournements de conversation.
5. `NeronCommandDispatcher` et routes Goal: acces directs aux pipelines specialises.

Le Planner et le Goal Pipeline prenaient aussi des decisions d'execution
internes. Ces decisions de risque et d'autorisation ne sont pas des decisions
de routage utilisateur et restent bornees a leur workflow.

## Responsabilites observees

| Composant | Role theorique | Role reel avant | Role apres |
| --- | --- | --- | --- |
| Core Orchestrator | choisir une route | present mais non utilise par l'API principale | unique autorite de routage |
| Intent Router | classifier | classifiait et appliquait des priorites | classificateur consulte par le Core |
| Resolver | resoudre une capacite specialisee | essaye par defaut avant presque toutes les routes | execute uniquement la route `resolver` |
| Planner | produire un plan | produit des plans; parfois expose par des routes d'execution compatibles | planifie dans un pipeline deja selectionne |
| Goal Pipeline | executer un objectif explicite | appele directement par plusieurs surfaces | execute seulement apres decision Core |
| Runtime Governor | politique et autorisation runtime | politique runtime, pas routeur principal | consulte par le Core pour les routes lourdes |
| Agent Router | dispatcher technique | redecidait parfois la destination finale | execute une intention deja choisie |

## Flux apres

```text
Utilisateur
  -> surface d'entree
  -> CoreOrchestrator.decide()
  -> OrchestratorDecision
  -> executant specialise
  -> CoreResponse / SSE / message
```

Routes selectionnables:

- `llm_provider`
- `timer_engine`
- `memory_engine`
- `tool_router`
- `resolver`
- `agent_factory`
- `goal_pipeline`

Le Runtime Governor est consulte pour les routes complexes. Il autorise ou
limite l'execution; il ne choisit pas la route utilisateur.

## Decision structuree

Chaque decision contient:

```json
{
  "intent": "conversation",
  "selected_route": "llm_provider",
  "reason": "Conversation ou explication generale sans moteur specialise requis.",
  "complexity": "simple",
  "requires_llm": true,
  "requires_timer": false,
  "requires_memory": true,
  "requires_tool": false,
  "requires_resolver": false,
  "requires_agent_factory": false,
  "requires_goal_pipeline": false,
  "requires_governor": false
}
```

## Journalisation

Evenements ajoutes:

- `orchestrator_decision`
- `selected_route`
- `llm_provider_used`
- `timer_used`
- `memory_used`
- `tool_router_used`
- `resolver_used`
- `planner_used`
- `goal_pipeline_used`
- `governor_used`

`agent_factory_used` est aussi journalise pour tracer le builder canonique.

## Simplifications

- Le Resolver n'est plus essaye sur chaque message.
- Les conversations ne sont plus detournees par AgentRouter vers un agent
  dynamique avant le LLM.
- Telegram texte ne traite plus les commandes evolution en langage naturel
  avant le Core; les commandes `/evolution` explicites restent disponibles.
- `/goal`, `/goals/run` et Telegram `/goal` passent par la decision Core.
- `chat.send`, InternalGateway, `/input/text` et `/input/stream` convergent.
- Le minuteur reutilise l'APScheduler existant.

## Risques residuels

- `_legacy_text_input` reste dans `core/app.py` comme reference privee non
  enregistree. Il n'est appele par aucune route, mais doit etre supprime
  physiquement lors d'un nettoyage dedie.
- Les routes publiques `/planner/execute*` restent des surfaces de
  compatibilite capables de lancer une execution explicite.
- Le Goal Pipeline conserve ses decisions internes de risque, validation et
  poursuite d'etapes. Elles ne doivent pas redevenir du routage general.
- Les deux schedulers historiques (`core/modules/scheduler.py` et
  `core/scheduler/*`) restent distincts.
- Le chat Replit dormant du dashboard contournerait le Core s'il etait
  enregistre ulterieurement.

## Conclusion

- Decideur: `core.pipeline.orchestrator.CoreOrchestrator`.
- Intent Router: classification uniquement.
- Resolver, Planner, Goal Pipeline et Runtime Governor: moteurs specialises.
- Les formats publics principaux restent compatibles.
- Neron est operationnel apres redemarrage de `neron-core`.

## Validation finale

- Suite suivie: `482 passed`, 3 avertissements deprecation.
- Dashboard: `npm run build` reussi.
- Compilation: `python -m compileall` reussie.
- Runtime date/heure: `selected_route=timer_engine`, reponse 200.
- Runtime conversation: `selected_route=llm_provider`, reponse LLM 200.
- Journald: `orchestrator_decision`, `selected_route`, `timer_used`,
  `llm_provider_used` et `memory_used` observes.
- `pytest -q` sans exclusion reste bloque a la collecte par le fichier local
  non suivi `tests/test_tool_creator_v2.py`, qui importe `ToolNeed` absent de
  `core/tools/models.py`. Les fichiers non suivis `core/tools/*` associes
  existaient avant le chantier et n'ont pas ete modifies.
