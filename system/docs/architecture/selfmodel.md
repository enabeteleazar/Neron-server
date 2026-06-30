# SelfModel canonique

## Audit

Le SelfModel actif est `server/core/modules/self_model/service.py`. Il consolide
l'identité, l'état opérationnel et les événements récents sans devenir un
collecteur système autonome.

Les chemins suivants sont conservés uniquement comme façades de compatibilité :

- `server/core/self_model/self_model.py`
- `server/modules/self_model/self_model.py`

`server/modules/self_model/self_model_loop.py` et
`system/deploy/neron-self-model-loop.service` sont legacy. L'unité reste
désactivée : la consolidation est appelée par le Core et alimentée par l'Event
Bus. Elle ne doit pas être réactivée.

## Sources de vérité

Le SelfModel agrège en lecture :

- Identity pour l'identité ;
- Status pour les ressources et l'état opérationnel ;
- Service Registry pour les services actifs connus ;
- Provider Registry pour les providers et leurs capacités ;
- A2A Client et Agent Registry pour les agents ;
- Memory Provider pour la disponibilité mémoire ;
- Goal Engine et le runtime Goal pour les objectifs.

Il n'appelle directement ni `systemctl`, ni SQLite, ni Obsidian, ni Ollama.

`open_meteo` est un agent A2A et apparaît exclusivement dans
`/selfmodel/agents`. Il ne fait pas partie du Provider Registry. Les providers
actuels exposés par `/selfmodel/providers` sont `oblivia` et `llm`.

Chaque entrée topologique expose :

- `kind` : `provider` ou `agent` ;
- `runtime_type` : `persistent`, `temporary` ou `unknown` ;
- `managed_by` : registre ou moteur responsable.

Les providers sont persistants et gérés par `provider_registry`. Les agents
peuvent être permanents ou temporaires et être gérés par `agent_registry`,
`a2a` ou `goal`.

La règle d'architecture est stricte :

- Goal Engine développe les agents et modules nécessaires ;
- un futur Provider Agent gérera leur présence et leur exécution ;
- les Providers actuels exposent uniquement des capacités stables.

Le Provider Agent est seulement documenté ici : il n'est pas créé dans cette
phase.

## Utilisation par Goal Engine

Avant l'analyse d'un objectif, Goal Engine charge un contexte SelfModel en
lecture : état, capacités, providers, agents, mémoire et architecture. Il
privilégie l'agent ou le provider déclaré dans cette vue. Si le SelfModel est
indisponible ou périmé, un fallback local contrôlé reste disponible et son
utilisation est signalée dans les diagnostics du goal.

Les résultats Goal exposent :

- `selfmodel_used`
- `selfmodel_available`
- `selfmodel_error`
- `selected_provider_from_selfmodel`
- `selected_agent_from_selfmodel`
- `selfmodel_decision_reason`

## API

Toutes les routes sont protégées par l'authentification centralisée :

- `GET /selfmodel/status`
- `GET /selfmodel/identity`
- `GET /selfmodel/capabilities`
- `GET /selfmodel/providers`
- `GET /selfmodel/services`
- `GET /selfmodel/agents`
- `GET /selfmodel/memory`
- `GET /selfmodel/goals`
- `GET /selfmodel/architecture`

Les anciennes routes `/self-model/status` et `/self-model/context` restent
disponibles pour compatibilité.
