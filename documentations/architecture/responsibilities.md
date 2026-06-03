# Neron OS Responsibilities

This file is the operational responsibility map for the agent/tool creation
workflow. Public routes and legacy imports stay compatible, but new code should
follow the target ownership below.

## Target Flow

User -> Intent Router -> Planner -> ProjectManager -> AgentBuildOrchestrator ->
ActionExecutor/Codex -> Tests -> Registry -> Notification

## Component Map

| Module | Current responsibility | Target responsibility | Duplicate risk | Action |
| --- | --- | --- | --- | --- |
| `core/pipeline/intent/intent_router.py` | Classifies user text into intents. | Single intent classification layer. | Competing keyword/NLP classifiers can diverge. | Keep; route `agent_creation` and `tool_creation` here. |
| `core/pipeline/routing/agent_router.py` | Dispatches intents to agents/services. | Dispatch only; no agent file creation. | Legacy `AgentFactoryAgent` path. | Adapted to call `AgentBuildOrchestrator` for creation. |
| `core/planning/planner.py` | Builds structured plans. | Planner produces specs/steps only. | Can be confused with executors. | Keep; no filesystem writes or execution. |
| `core/api/planner_routes.py` | Public planner compatibility routes, including legacy execute endpoints. | Compatibility API around planner/orchestrator/task execution. | `/planner/execute` overlaps orchestration. | Keep public endpoints; document as compatibility. |
| `core/goals/goal_orchestrator.py` | Goal -> plan -> tasks -> risk -> task execution. | Goal workflow coordinator. | Can appear to create agents through task execution. | Keep; agent steps create proposals, not files. |
| `core/task_system/task_manager.py` | Stores task state. | Task state only. | Overlap with projects for long builds. | Keep; tasks are plan steps, not build truth. |
| `core/projects/manager.py` | Stores long-running project/build state. | Source of build progress/status. | Overlap with TaskManager status. | Keep; agent/tool build state lives here. |
| `core/task_system/task_executor.py` | Executes known task actions. | Execute approved task actions only. | Can call `AgentCreator`. | Keep; agent actions produce proposals only. |
| `core/agent_factory/agent_creator.py` | Legacy-safe proposal creator. | Compatibility facade for proposal records. | Name suggests code creation. | Keep; explicitly no code writes/execution. |
| `core/agent_factory/factory_agent.py` | Legacy agent factory wrote draft files. | Compatibility facade to `AgentBuildOrchestrator`. | Duplicate creation workflow. | Adapted/deprecated. |
| `core/agent_factory/build_orchestrator.py` | Creates files, validates, tests, registers, verifies. | Main agent/tool build orchestrator. | Must not be bypassed for real builds. | Keep as canonical build path. |
| `core/agent_factory/registry.py` | Loads generated agents. | Dynamic generated-agent registry. | Overlaps runtime agent registry. | Keep as loader backing runtime manager. |
| `core/runtime/agents/agent_runtime_manager.py` | Lists/runs generated agents. | Runtime source for generated agent availability. | Overlaps control-plane registry. | Keep for generated runtime. |
| `core/control_plane/registry.py` | Registers services/agents in control plane. | Service/control-plane registry. | Name overlaps dynamic registry. | Keep; distinct scope. |
| `core/runtime/tools/tool_manager.py` | Runtime tool registry. | Runtime tool execution registry. | Separate from agents. | Keep. |
| `core/cognitive/action_executor.py` | Cognitive action executor. | Execute selected cognitive actions. | Can call planner in restore path. | Keep; not part of build creation path. |
| `core/memory/persistent_store.py` | Persistent conversation/fact store. | Operational memory. | Overlap with goals/tasks/projects. | Keep; store facts/results, not workflow state. |
| `memory/obsidian/*`, `agents/memory/obsidian_agent.py` | Obsidian notes/search/index. | Optional documentation and retrieval. | Could become required operational storage. | Keep optional; build path must not import it. |
| `core/goals/*`, `core/goal_system/*` | Goal APIs and legacy goal state. | Goal lifecycle and compatibility. | Two goal stores exist. | Keep; avoid format-breaking migration. |
| `core/modules/scheduler.py`, `core/modules/autonomous/scheduler.py` | Periodic/autonomous runners. | Scheduling loops only. | Multiple schedulers. | Keep; scopes differ, mark future consolidation candidate. |

## Rules

- Planner creates plans/specs and must not write files, register agents, or run tests.
- `AgentBuildOrchestrator` is the only canonical path for real agent/tool builds.
- `AgentCreator` and legacy task execution produce proposals only.
- `ProjectManager` tracks long-running build/project status.
- `TaskManager` tracks executable plan tasks.
- `Memory` records useful facts/results; it is not workflow state.
- Obsidian is optional documentation/search context and must not be required for builds.
- A user-facing "created/completed" response requires technical proof: validation,
  tests, registry status, and runtime availability.

## Known Compatibility Left In Place

- `/planner/execute/{plan_id}` remains for public compatibility even though new
  creation work should go through `/agents/build` or the intent router.
- `/goal` and `/goals/run` remain public aliases for the goal orchestrator.
- `AgentFactoryAgent` remains importable but delegates to `AgentBuildOrchestrator`.
- `AgentCreator` remains importable for legacy plan/task proposal flows.
