# Goal Execution Engine

## Purpose

`core/goals/execution_engine.py` owns the persistent execution state of
asynchronous goals. `ProjectManager` still owns build projects, but goal
observation no longer depends on reconstructing a run from project and plan
records.

## Persistence

The engine uses `/etc/neron/data/neron_state.sqlite3` through the existing
`SQLiteStore`. Every connection keeps:

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
```

`goal_runs` stores the latest execution snapshot. `goal_events` is an
append-only transition history. State updates and their matching event are
written in the same `BEGIN IMMEDIATE` transaction.

Tracked steps are:

```text
planning
code_generation
validation
compile
tests
business_validation
sandbox
runtime_governor
registry
verification
completed | failed
```

## API

- `POST /goal`: creates the legacy goal, enqueues a `goal_run`, records the
  `queued` event, starts background processing, and returns HTTP 202.
- `GET /goal/{goal_id}/status`: reads `goal_runs` first and enriches the result
  with plan/project validation details for compatibility.
- `GET /goal/{goal_id}/events`: returns ordered persistent events.
- `GET /goals`: returns `count` and the persistent runs, plus legacy goals that
  do not have a run yet.

`POST /goals/run`, `/goals/active`, `/projects`, and the legacy goal mutation
routes keep their existing behavior.

## Restart Recovery

At Core startup, every `goal_run` with status `running` becomes
`interrupted`. The engine records an `interrupted` event and preserves the
last known plan, project, agent, and progress fields.

Interrupted runs are not restarted automatically. Automatic replay would need
idempotency guarantees for code generation, registry promotion, and runtime
reload. A later recovery policy can explicitly decide whether a run is safe to
resume or must be restarted from a known checkpoint.

Queued runs are left queued because they never claimed execution.

## Remaining Limits

- There is no automatic resume or retry policy.
- Worker threads cannot forcibly stop a blocking subprocess during shutdown.
- Events describe pipeline transitions but do not yet store resumable
  checkpoints or cancellation tokens.
- Concurrent builds targeting the same agent slug still need a per-slug lock.
- Sandbox transitions use the explicit event statuses `sandbox_started`,
  `sandbox_passed`, and `sandbox_failed`.
