# Goal Agent Pipeline

## Scope

This document describes the hardened Phase 2.1 pipeline used when `/goal`
requests the creation of a dynamic agent:

```text
/goal
  -> GoalOrchestrator
  -> AutonomousPlanner
  -> AgentCreator
  -> AgentBuildOrchestrator
  -> CodexRunner (codex/hybrid modes only)
  -> validation and tests
  -> BusinessValidator
  -> RuntimeGovernor
  -> DynamicAgentRegistry
  -> AgentRuntimeManager
```

The pipeline reuses the existing Planner, Agent Creator, build orchestrator,
Codex runner, registry, and runtime. It does not introduce parallel
implementations.

## Component Responsibilities

| Component | Responsibility | Must not do |
| --- | --- | --- |
| `GoalOrchestrator` | Own the goal-to-plan workflow and correlate IDs | Write generated agent files directly |
| `AutonomousPlanner` | Produce structured steps | Promote or execute generated code |
| `AgentCreator` | Persist a traceable proposal | Write or execute production code |
| `AgentBuildOrchestrator` | Build, validate, test, run business validation, govern, promote, and verify | Bypass validation or the Governor |
| `CodexRunner` | Optionally generate workspace code and tests | Write to `core/agents/generated` |
| `BusinessValidator` | Execute the workspace agent in an isolated process and verify a business scenario | Promote or reload runtime agents |
| `RuntimeGovernor` | Authorize or refuse promotion | Load agents |
| `DynamicAgentRegistry` | Load valid generated agent modules | Decide whether promotion is allowed |
| `AgentRuntimeManager` | Reload and execute registered agents | Promote workspace files |

## Persisted State

The workflow is correlated with these identifiers:

- `goal_id`: lifecycle record in `data/goals_state.json`.
- `plan_id`: planner record in `data/plans.jsonl`.
- `agent_request_id`: Agent Creator proposal in
  `data/agent_creator_proposals.jsonl`.
- `build_project_id`: build record in `data/projects.json`.

The build project metadata stores `goal_id`, `plan_id`, and
`agent_request_id`. This allows observation while the synchronous `/goal`
request is still executing.

## Observable Build States

Every build project exposes:

- `status`
- `current_step`
- `progress`
- `validation_status`
- `compile_status`
- `test_status`
- `business_validation_status`
- `business_validation_result`
- `governor_status`
- `registry_status`
- `runtime_status`
- `steps`
- `test_results`
- `error`

Normal step order:

```text
created
planning
code_generation
validation
compile
tests
business_validation
runtime_governor
registry
verification
completed
```

Codex failures can add `codex` as a terminal failure step.

## Promotion Invariants

Promotion to `core/agents/generated` is forbidden unless all of these
conditions are true:

1. The generated workspace file passes `validate_agent`.
2. Python compilation succeeds.
3. The generated pytest file succeeds.
4. Business validation executes the workspace agent and its response satisfies
   the inferred scenario.
5. `RuntimeGovernor.authorize_agent_promotion` returns `True`.

Reliable built-in scenarios currently cover Easter 2027, the time remaining
before Christmas, and IPv4 subnet calculation. Other goals use a compatibility
fallback requiring a non-empty successful response. The fallback rejects
generic claims such as `Agent disponible pour`, `Je suis un agent`, and
`Réponse déterministe`.

The shared legacy `promote_agent` helper also consults the Runtime Governor.
Existing callers remain compatible because its original positional arguments
are unchanged. The legacy conversational promotion route also runs the
associated pytest file when one exists and refuses promotion on failure.

After copying, the pipeline requires:

1. The destination file exists.
2. `DynamicAgentRegistry` can load and identify the agent.
3. `AgentRuntimeManager` can reload and execute the agent with a non-empty
   response.

If registry or runtime verification fails, the promotion is rolled back. A
previous destination file is restored byte-for-byte; otherwise the new file is
removed. The runtime is reloaded after rollback.

## Failure Matrix

| Failure | Promotion attempted | Final registry state | Runtime state |
| --- | --- | --- | --- |
| Codex failure in `codex` mode | No | `not_registered` | `not_available` |
| Validation failure | No | `not_registered` | `not_available` |
| Compile failure | No | `not_registered` | `not_available` |
| Test failure | No | `not_registered` | `not_available` |
| Business validation failure | No | `not_registered` | `not_available` |
| Governor refusal | No | `not_registered` | `not_available` |
| Registry load failure | Rolled back | `not_registered` | Reloaded |
| Runtime verification failure | Rolled back | `not_registered` | `failed` |
| Unhandled post-copy exception | Rolled back | `not_registered` | Reloaded |

The goal is marked `failed` for every failed or refused agent build. A goal is
marked `completed` only after successful runtime verification.

## Observation Endpoint

```http
GET /goal/{goal_id}/status
```

Successful response:

```json
{
  "goal_id": "goal_123",
  "status": "running",
  "current_step": "registry",
  "progress": 85,
  "plan_id": "plan-123",
  "agent_slug": "weather_agent",
  "codex_used": true,
  "validation_status": "passed",
  "compile_status": "passed",
  "test_status": "passed",
  "business_validation_status": "passed",
  "business_validation_result": {
    "ok": true,
    "status": "passed"
  },
  "governor_status": "allowed",
  "registry_status": "registered",
  "runtime_status": "pending",
  "errors": []
}
```

The endpoint returns `404 Goal not found` for an unknown `goal_id`.

`progress` is an integer percentage from 0 to 100. During a build, project
progress has priority over goal progress because it is more precise.

## Compatibility

- `POST /goal` and `POST /goals/run` are unchanged.
- Existing `/goals`, planner, project, registry, and runtime routes are
  unchanged.
- `AgentFactoryAgent`, direct proposal approval, and manual promotion remain
  available.
- `tracking_context` on `AgentBuildOrchestrator.build_from_request` is
  optional.
- Goal orchestration retries old build facades that do not accept
  `tracking_context`.
- Existing goal and project files remain readable because all schema changes
  are additive.

## Operational Checks

Phase 2.2 asynchronous acceptance and SQLite persistence are documented in
`docs/async_goal_sqlite.md`.

Inspect one workflow:

```bash
curl -s http://localhost:8010/goal/GOAL_ID/status | jq
```

Required release validation:

```bash
pytest -q
```

## Phase 2.2 Recommendations

1. Make build execution asynchronous and return `202 Accepted` so observation
   can be used without holding the original HTTP connection.
2. Add immutable transition events for goal, plan, build, registry, and runtime
   state changes.
3. Add per-goal cancellation with rollback before promotion.
4. Replace process-local runtime state with a restart-safe health record.
5. Add concurrency locking per agent slug to prevent simultaneous builds of
   different specifications targeting the same file.
6. Require signed validation evidence for legacy manual promotions if those
   paths are kept beyond Phase 2.2.
