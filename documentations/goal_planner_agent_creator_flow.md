# Flux Goal -> Planner -> Agent Creator

## Flux reel

1. `core/goals/routes.py`
   - `POST /goals/run` et `POST /goal` reçoivent un objectif.
   - Ils appellent `GoalOrchestrator.run_goal`.
   - `POST /goals` conserve son comportement historique : creation simple d'objectif.

2. `core/goals/goal_orchestrator.py`
   - Cree ou reutilise l'objectif via `GoalManager`.
   - Appelle `AutonomousPlanner.create_plan`.
   - Persiste le plan dans `PlanStorage`.
   - Cree les taches via `TaskManager.create_tasks_from_plan`.
   - Evalue le risque avec `CriticEngine`.
   - Execute seulement si la politique de risque l'autorise.
   - Publie des traces event bus : `goal.created`, `planner.plan_created`, `agent_creator.proposal_created`.

3. `core/planning/planner.py`
   - Transforme un objectif contenant `agent` en plan structure.
   - Les etapes `define_agent` et `create_skeleton` ciblent `agent_creator`.

4. `core/task_system/task_executor.py`
   - Route les actions `agent_creator` vers la facade `AgentCreator`.
   - Ne genere pas de code.
   - Ne lance pas Codex.
   - Marque la proposition comme `pending_human_validation`.

5. `core/agent_factory/agent_creator.py`
   - Prepare un cahier des charges JSON.
   - Ecrit une trace dans `/etc/neron/data/agent_creator_proposals.jsonl`.
   - Propose des fichiers sous `workspace/agents` et `tests`, jamais une ecriture directe dans `core/agents`.

## Limites actuelles

- Agent Creator ne produit pas encore de code.
- Codex CLI n'est pas appele automatiquement.
- La promotion vers `core/agents/generated` doit rester une etape separee avec validation humaine.
- `POST /goals` ne declenche pas le planner pour conserver le format public existant.

## Tests

Commandes utiles :

```bash
venv/bin/python -m pytest tests/test_goal_agent_creation_flow.py -q
venv/bin/python -m pytest -q
```

## Validation runtime

```bash
curl -s http://localhost:8010/health | jq
curl -s http://localhost:8010/self-model/context | jq
curl -s http://localhost:8010/goals/active | jq
curl -s -X POST http://localhost:8010/goals/run \
  -H "Content-Type: application/json" \
  -d '{"objective":"Créer un agent météo capable de répondre à une demande météo simple.","source":"api"}' | jq
```

## Logs et traces

```bash
journalctl -u neron-core -n 200 --no-pager
tail -n 20 /etc/neron/data/plans.jsonl
tail -n 20 /etc/neron/data/agent_creator_proposals.jsonl
```

## Prochaine integration Codex

La future delegation a Codex doit partir d'une proposition `pending_human_validation`.
Codex pourra generer le code uniquement apres validation explicite, puis deposer le resultat
dans un espace de staging avant toute promotion vers les agents charges par le runtime.
