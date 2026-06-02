# Architecture Telegram

Date: 2026-06-02

## Decision

La surface Telegram principale est `core/agents/communication/telegram_agent.py`.

Telegram ne doit pas manipuler directement les orchestrateurs internes complexes. Il transmet des commandes metier a `core.orchestration.command_dispatcher.NeronCommandDispatcher`.

## Flux

Exemple `/goal créer un agent météo`:

```json
{
  "source": "telegram",
  "type": "goal_request",
  "payload": "créer un agent météo",
  "user_id": "<chat_id>"
}
```

Le dispatcher route ensuite vers le composant interne adapte:

- `goal_request` -> GoalOrchestrator
- `approve_plan` -> GoalOrchestrator
- `execute_plan` -> GoalOrchestrator
- `active_goal` -> lecture GoalSystem compatible
- `evolution_text` -> EvolutionSupervisor

## Compatibilite

Les handlers Telegram existants restent presents:

- `/goal`
- `/goal_active`
- `/approve`
- `/execute`
- `/evolution`
- `/evolution_status`
- `/accept_evolution`
- `/reject_evolution`
- `/evolution_stop`

`route_evolution_telegram_text()` reste disponible pour les tests et integrations existantes, mais delegue au dispatcher.

## Objectif technique

Le module Telegram ne reference plus directement:

- `core.goals.goal_orchestrator`
- `core.evolution.supervisor`

Cela reduit le couplage statique et limite les cycles d'import.

