# Async Goal And SQLite State

## Scope

Phase 2.2 keeps the existing `GoalOrchestrator`, `ProjectManager`,
`AgentBuildOrchestrator`, registry, and runtime. It changes how `/goal` is
accepted and how critical workflow state is persisted.

```text
POST /goal
  -> create goal with status queued
  -> persist in SQLite and legacy JSON
  -> return HTTP 202
  -> GoalBackgroundRunner
  -> GoalOrchestrator
  -> Planner
  -> AgentBuildOrchestrator
  -> validation, compilation, tests
  -> RuntimeGovernor
  -> Registry
  -> Runtime verification
```

`POST /goals/run` remains synchronous for compatibility.

## Async API

`POST /goal` returns before planning or agent generation starts:

```json
{
  "accepted": true,
  "goal_id": "goal_123",
  "status": "queued",
  "status_url": "/goal/goal_123/status"
}
```

The HTTP status is `202 Accepted`.

The background runner maintains one tracked asyncio task per goal. Each task
starts a dedicated worker thread because the build pipeline contains blocking
subprocess calls. The worker uses the existing asynchronous
`GoalOrchestrator`; no second orchestrator or execution pipeline is introduced.

The runner:

- prevents duplicate submission for one `goal_id`;
- records uncaught exceptions as a failed goal;
- exposes a wait operation for controlled tests;
- cancels tracked wrapper tasks during FastAPI shutdown.

## Status API

`GET /goal/{goal_id}/status` reads state through the existing managers, whose
primary persistence is now SQLite:

```json
{
  "goal_id": "goal_123",
  "status": "completed",
  "current_step": "completed",
  "progress": 100,
  "plan_id": "plan_123",
  "project_id": "agent_weather_123",
  "agent_slug": "weather_agent",
  "codex_used": true,
  "validation_status": "passed",
  "compile_status": "passed",
  "test_status": "passed",
  "governor_status": "allowed",
  "registry_status": "registered",
  "runtime_status": "available",
  "error": null,
  "errors": [],
  "steps": []
}
```

Public workflow statuses normalize `plan_finished` to `completed`. Failed,
refused, and risk-blocked workflows are exposed as `failed`.

## SQLite Store

Database:

```text
/etc/neron/data/neron_state.sqlite3
```

`core/storage/sqlite_store.py` applies an idempotent migration at
initialization and configures every connection with:

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
```

All state mutations use `BEGIN IMMEDIATE`, followed by explicit commit or
rollback.

Tables:

| Table | Purpose |
| --- | --- |
| `goals` | Goal lifecycle, progress, error, and full payload |
| `goal_runs` | Authoritative current state for asynchronous goal execution |
| `goal_events` | Ordered immutable goal execution transitions |
| `projects` | Build project state and goal/plan correlation |
| `workflows` | Planner workflow payloads |
| `workflow_steps` | Ordered project and workflow transitions |
| `test_results` | Ordered build test evidence |

Payload columns preserve additive fields without requiring a schema migration
for each new observable attribute. Indexed columns support status correlation
without parsing JSON.

## Legacy Compatibility

The existing files remain supported:

- `data/goals_state.json`
- `data/projects.json`
- `data/plans.jsonl`
- `data/tasks.json`

Legacy rows missing from SQLite are imported automatically by identifier.
Existing SQLite rows are never overwritten by stale legacy payloads.
Subsequent writes use SQLite as the primary state and atomically mirror the
full compatible payload back to the legacy file.

No existing public manager method was removed. Existing JSON and JSONL readers
can continue operating during the migration period.

## Concurrency

SQLite serializes writers with WAL, `busy_timeout`, and `BEGIN IMMEDIATE`.
Within the Neron process, a shared reentrant lock is also assigned per database
or legacy file path.

This protects:

- goal creation and status updates;
- project creation, step updates, and test results;
- plan save/update operations;
- shared task updates used by parallel goal workflows;
- atomic legacy file replacement.

Two goals can therefore progress concurrently without a JSON
read-modify-write race or partial file content.

## Operational Checks

```bash
sqlite3 /etc/neron/data/neron_state.sqlite3 'PRAGMA journal_mode;'
sqlite3 /etc/neron/data/neron_state.sqlite3 'PRAGMA integrity_check;'
curl -s -X POST http://localhost:8010/goal \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Créer un agent de démonstration"}'
curl -s http://localhost:8010/goal/GOAL_ID/status
```

Release validation:

```bash
pytest -q
```

## Remaining Risks

- Worker threads cannot forcibly interrupt an active subprocess during service
  shutdown.
- Legacy file locking is process-local; SQLite remains the authoritative
  cross-process synchronization mechanism.
- Simultaneous builds targeting the same agent slug still need a per-slug
  build lock.
- Runs left in `running` are marked `interrupted` at Core startup and are not
  resumed automatically.
