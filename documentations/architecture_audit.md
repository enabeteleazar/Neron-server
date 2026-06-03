# Audit Architecture Neron OS

Date: 2026-06-02

## Portee

Audit de pre-production limite a la solidification du systeme existant. Aucune nouvelle fonctionnalite Phase 2 n'a ete demarree.

## Modules principaux

- API Core: `core/app.py`, FastAPI principal, inclut les routers self-model, world-model, goals, tasks, planner, projects, evolution, code-awareness et runtime-governor.
- SelfModel: `core/self_model/*`, boucle systemd `neron-self-model-loop.service`, et endpoints `/self-model/*`.
- WorldModel: `core/world_model/*`, `core/memory/world_model/*`, boucle `neron-world-model-loop.service`, endpoints `/world-model/*`.
- GoalSystem: `core/goals/*`, `core/goal_system/*`, endpoints `/goal`, `/goals`, `/goals/run`.
- Planner: `core/planning/*`, `core/api/planner_routes.py`, endpoints `/planner/*`.
- Agent Runtime: `core/runtime/agents/*`, `core/agent_factory/*`, registry dynamique `core/agent_factory/registry.py`.
- Evolution Engine: `core/evolution/*`, endpoints `/evolution/*`, execution Codex en arriere-plan.
- Memory: `core/memory/*`, `core/agents/core/memory_agent.py`, stockage sous `/etc/neron/data`.
- Event Bus: `core/events/*` et `core/runtime/events/*`.
- Watchdog: `core/agents/automation/watchdog_agent.py`, lance par `neron-core` au startup, pas par une unite `neron-watchdog.service` separee.

## Endpoints FastAPI detectes

Extraction reelle depuis `core.app.app`:

- Racine et sante: `/`, `/health`, `/status`, `/metrics`.
- Input: `/input/text`, `/input/stream`, `/input/audio`, `/input/voice`.
- Goals: `/goal`, `/goals`, `/goals/active`, `/goals/run`, `/goals/{goal_id}/complete`, `/goals/{goal_id}/fail`, `/goals/{goal_id}/progress`.
- Planner: `/planner/create`, `/planner/status`, `/planner/history`, `/planner/last`, `/planner/ready`, `/planner/from-goal`, `/planner/approve/{plan_id}`, `/planner/execute/{plan_id}`, `/planner/execute-approved/{plan_id}`, `/planner/generate-tasks/{plan_id}`, `/planner/risk/{plan_id}`, `/planner/sync-tasks`, `/planner/cleanup-duplicates`.
- Tasks: `/tasks`, `/tasks/status`, `/tasks/running`, `/tasks/next`, `/tasks/next/start`, `/tasks/execute-next`, `/tasks/{task_id}`, `/tasks/{task_id}/start`, `/tasks/{task_id}/complete`, `/tasks/{task_id}/fail`, `/tasks/{task_id}/cancel`, `/tasks/{task_id}/status`, `/tasks/done/clear`.
- Evolution: `/evolution/status`, `/evolution/propose`, `/evolution/proposals`, `/evolution/accept/{proposal_id}`, `/evolution/reject/{proposal_id}`, `/evolution/stop`, `/evolution/runs`.
- Code awareness: `/code-awareness/map`, `/code-awareness/tree`, `/code-awareness/search`, `/code-awareness/read`, `/code-awareness/analyze`, `/code-awareness/dependencies`, `/code-awareness/architecture`.
- Self/World/Cognitive: `/self-model/context`, `/world-model/context`, `/world-model/status`, `/world-model/summary`, `/cognitive-core/state`, `/cognitive-core/report`.
- Runtime et historiques: `/runtime/governor/policy`, `/actions/history`, `/actions/latest`, `/critic/history`, `/critic/latest`, `/projects`, `/projects/search`, `/projects/{project_id}`, `/projects/diagnostics/failures`.
- Configuration/persona: `/memory`, `/personality/state`, `/personality/history`, `/personality/reset`, `/nlp/parse`, `/ha/reload`.

## Services systemd

Unites critiques verifiees:

- `neron-core.service`: actif, lance `uvicorn core.app:app` sur le port 8010.
- `neron-self-model-loop.service`: actif, lance `python3 -m core.self_model.self_model_loop`.
- `neron-world-model-loop.service`: actif, lance `python3 -m core.world_model.world_model_loop`.
- `neron-cognitive-loop.service`: actif, lance `core/autonomous/run_cognitive_loop.py`.
- `neron-watchdog.service`: absent. Le watchdog est integre au startup de `neron-core` via `start_watchdog()` et `start_watchdog_bot()`.

Correction appliquee: `scripts/install_systemd.sh` installait `deploy/neron.service`, fichier inexistant. Il installe maintenant les unites existantes `neron-core`, `neron-self-model-loop`, `neron-world-model-loop`, `neron-cognitive-loop`, `neron-llm`, `neron-doctor`.

## Agents

Agents maintenus detectes:

- Core: LLM, Memory, SelfModel, System, Todo.
- IO: Weather, Wiki, News, STT, TTS.
- Automation: Home Assistant, Watchdog.
- Communication: Telegram, Twilio, Web.
- Development: CodeAgent, CodeAuditAgent.
- Generated: `event_countdown_agent`, `meteo_agent`, `test_agent`.
- Factory/runtime: AgentCreator, AgentBuildOrchestrator, DynamicAgentRegistry, AgentRuntimeManager.

## Boucles autonomes

- `SelfMonitor` dans `core/app.py` via `asyncio.create_task(get_self_monitor().start())`.
- Watchdog via `start_watchdog()` dans `core/app.py`.
- Scheduler APScheduler via `core/modules/scheduler.py`.
- SelfModel loop via service dedie.
- WorldModel loop via service dedie.
- Cognitive loop via service dedie.
- Evolution Codex jobs via worker background `asyncio.create_task`.

## Dependances

Le mapper local a detecte environ 250 modules et 422 dependances internes/adjacentes. Cycles detectes par analyse statique:

- `core.agents.communication.telegram_agent -> core.evolution.supervisor -> core.agents.communication.telegram_agent`
- `core.agents.communication.telegram_agent -> core.goals.goal_orchestrator -> core.agents.communication.telegram_agent`

Ces cycles sont actuellement portes par des imports de notification en chemin d'execution, pas par des imports top-level bloquants. Risque residuel: couplage fort Telegram <-> orchestration.

## Corrections appliquees pendant l'audit

- `fix(systemd): install existing neron units`
- `fix(core): allow logging fallback outside var log`
- `fix(status): repair legacy core imports`

