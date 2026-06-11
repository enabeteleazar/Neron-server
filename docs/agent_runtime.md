# Agent Runtime V1

`core/agent_runtime` est le point d'entrée central pour charger et exécuter les
agents enregistrés.

## Flux

```text
Capability Resolver ou Task Scheduler
  -> Agent Runtime
  -> Registry
  -> ExecutionContext
  -> ToolBinding
  -> Tool Runtime
  -> réponse et historique SQLite
```

Le Resolver ne lance plus directement `Agent.execute()`. Le gestionnaire
historique délègue lui aussi à `AgentRuntime` afin de conserver la compatibilité
des appels existants.

## Contrats

- `AgentInstance` contient l'agent chargé, sa spec et ses tools liés.
- `ExecutionContext` contient la requête, le contexte, les metadata et les
  bindings disponibles.
- `ToolBinding` vérifie le Tool Registry et délègue l'exécution au Tool Runtime.
- `AgentExecutionResult` normalise le statut, la réponse, l'erreur et la durée.

Les tools doivent être déclarés dans `AGENT_SPEC.tools` ou
`AGENT_SPEC.required_tools`. Un tool absent fait échouer l'exécution avant
l'appel de l'agent.

## Persistance et API

Chaque exécution est stockée dans `agent_runtime_executions`, d'abord avec le
statut `running`, puis `completed` ou `failed`.

- `GET /agents/runtime/status`
- `GET /agents/runtime/executions`
- `GET /agents/runtime/executions/{execution_id}`
- `POST /agents/runtime/run/{agent_slug}`

Les événements structurés `agent_runtime_started`,
`agent_runtime_completed` et `agent_runtime_failed` contiennent l'identifiant,
le slug, le statut et la durée.

## Limites V1

- Pas de mémoire conversationnelle durable propre au runtime.
- Pas de timeout ou d'annulation d'une exécution déjà lancée.
- Les politiques de concurrence restent portées par le Task Scheduler et le
  Runtime Governor.
