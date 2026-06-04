# Flux Goal -> Planner -> Agent Creator

## Flux /goal

1. `core/goals/routes.py`
   - `POST /goals/run` et `POST /goal` recoivent un objectif.
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

4. `core/goals/goal_orchestrator.py`
   - Pour un plan de creation d'agent a risque faible, appelle directement `AgentBuildOrchestrator`.
   - Ne bloque plus les creations normales sur une validation humaine.
   - Bloque les demandes sensibles : systemd, services systeme, secrets, securite, suppression de donnees.

5. `core/agent_factory/agent_creator.py`
   - Prepare une proposition JSON.
   - Ecrit une trace dans `/etc/neron/data/agent_creator_proposals.jsonl`.
   - Respecte les noms explicites, par exemple `nomme audit_agent_test`.
   - Reste disponible pour compatibilite et pour les flux a risque ou legacy.

## Flux d'approbation humaine

1. Un humain approuve avec :

   ```bash
   curl -X POST http://localhost:8010/agents/proposals/{agent_request_id}/approve \
     -H "X-API-Key: $NERON_API_KEY"
   ```

2. `core/projects/routes.py`
   - Retrouve la proposition via `AgentCreator`.
   - Refuse toute proposition qui n'est pas `pending_human_validation`.
   - Marque la proposition `human_approved`.
   - Utilise par defaut le mode `deterministic`.
   - Appelle `AgentBuildOrchestrator.build_from_request` en mode `deterministic`.

3. `core/agent_factory/build_orchestrator.py`
   - Genere l'agent dans `workspace/agents`.
   - Genere le test dans `workspace/agent_tests`.
   - Valide l'agent.
   - Lance `py_compile`.
   - Lance `pytest` sur le test genere.
   - Enregistre l'agent dans `core/agents/generated`.

4. `core/runtime/agents/agent_runtime_manager.py`
   - La route appelle `get_agent_runtime_manager().reload()`.
   - Le runtime recharge le registry existant et liste l'agent.

## Modes d'approbation

### Mode deterministic

Le mode `deterministic` est le mode stable et le comportement par defaut.

```bash
curl -X POST http://localhost:8010/agents/proposals/{agent_request_id}/approve \
  -H "X-API-Key: $NERON_API_KEY"
```

Il peut aussi etre demande explicitement :

```bash
curl -X POST http://localhost:8010/agents/proposals/{agent_request_id}/approve \
  -H "X-API-Key: $NERON_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode":"deterministic"}'
```

Ce mode utilise uniquement `AgentBuildOrchestrator` et conserve le pipeline valide :
generation, validation, tests, registry, reload runtime.

### Mode hybrid

Le mode `hybrid` est le mode Codex-assisted recommande pour experimenter :

- Neron genere d'abord le squelette deterministe dans `workspace/agents` et `workspace/agent_tests`.
- Codex recoit une mission limitee a ces deux chemins workspace.
- Codex peut ameliorer l'agent et le test, mais ne doit jamais ecrire dans `core/agents/generated`.
- Si Codex echoue, Neron continue avec le squelette deterministe et retourne `codex_fallback=true`.
- Neron garde ensuite toute la chaine de controle : validation, `py_compile`, `pytest`, registry, runtime reload.

### Mode codex

Le mode `codex` pur demande a Codex de produire l'agent et le test dans le workspace.

En cas d'echec Codex, le build echoue proprement, aucun agent n'est promu et le runtime n'est pas recharge.

Regles :

- Codex travaille uniquement dans `workspace/agents` et `workspace/agent_tests`.
- Codex ne doit jamais ecrire directement dans `core/agents/generated`.
- Neron restaure `core/agents/generated` si une ecriture directe Codex est detectee.
- Neron lance validation, `py_compile`, `pytest`, promotion et runtime reload uniquement apres generation workspace valide.
- Les sorties Codex exposees par l'orchestrateur redigent les secrets et masquent le prompt dans la commande.
- La route ne fait jamais `commit` ni `push` automatiquement.

`POST /agents/build` accepte maintenant :

```json
{
  "query": "Créer un agent nommé demo_agent",
  "build_mode": "deterministic"
}
```

`build_mode` peut valoir `deterministic`, `hybrid` ou `codex`.

## Garanties

- Aucun nouveau registry n'est cree.
- Aucun nouveau runtime n'est cree.
- Le mode deterministe existant reste le comportement par defaut.
- Codex n'est jamais autorise a promouvoir lui-meme dans `core/agents/generated`.
- La promotion vers `core/agents/generated` reste faite par Neron, apres validation et tests.
- Une proposition legacy deja approuvee ne peut pas etre reapprouvee.

## Reponse API

`POST /agents/proposals/{agent_request_id}/approve` retourne :

- `agent_request_id`
- `mode`
- `proposal_status`
- `build_status`
- `created_files`
- `registered_agent`
- `runtime_reload`
- `errors`
- `project`
- `build`

En mode `codex`, la reponse retourne :

- `agent_request_id`
- `mode`
- `proposal_status`
- `codex_result`
- `test_results`
- `runtime_reload`
- `errors`

`AgentBuildOrchestrator.build_from_request` retourne aussi :

- `build_mode`
- `codex_used`
- `codex_ok`
- `codex_fallback`
- `codex_error`

## Tests utiles

```bash
venv/bin/python -m pytest -q tests/test_tracked_agent_workflow.py tests/test_goal_agent_creation_flow.py
venv/bin/python -m pytest -q tests
```
