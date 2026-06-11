# Task Scheduler V2

## Purpose

The Task Scheduler answers:

```text
Who must do what, in which order, and when is it ready to run?
```

V2 persists executable tasks and dependency chains in SQLite and can execute
them continuously through a bounded asyncio worker.

## Boundaries

The Task Scheduler is not the Goal Engine.

- The Goal Engine tracks a user or system objective, planning, risk, builds,
  validation, and long-running goal state.
- The Task Scheduler executes concrete ordered actions such as three tool
  calls.

The Task Scheduler is not the Capability Resolver.

- The Capability Resolver decides whether to answer, use a capability, or
  create one.
- The resolver may enqueue a scheduler chain after making that decision.

The Task Scheduler is not Agent Runtime.

- Agent Runtime loads and executes one registered agent.
- The scheduler decides when an agent execution task is ready and records its
  outcome.

The existing legacy TaskManager remains available for planner compatibility
under `/tasks/legacy/...`. The central `/tasks` read, run, and cancel endpoints
now expose the SQLite scheduler.

## Model

`ScheduledTask` stores:

- `task_id`, `title`, `kind`, `status`, and `priority`;
- `payload`, `result`, and `error`;
- `depends_on`;
- creation, update, start, and finish timestamps;
- extensible `metadata`.

Kinds:

- `tool_execution`
- `agent_execution`
- `goal_execution`
- `notification`
- `composite`

Lifecycle:

```text
queued -> running -> completed
queued -> running -> failed
queued -> running -> queued    (retry)
queued -> blocked
running -> interrupted         (process restart)
queued/running/blocked -> cancelled
```

A task remains queued while a dependency is still queued or running. It
becomes blocked when a dependency is failed, blocked, cancelled, or missing.

## Persistence

Tasks are stored in the shared Néron SQLite database in:

```text
scheduler_tasks
```

Each row has indexed kind/status/priority fields and a complete JSON payload.
Creating a new `SchedulerStore` over the same database restores all tasks.

At Core startup, tasks left in `running` become `interrupted`. Their metadata
records `recovery_reason=scheduler_restarted` and `recovered_at`.

## Worker

The worker is part of the FastAPI lifespan. It uses asyncio tasks and never
blocks the event loop, Telegram, or HTTP request handling.

Configuration:

```text
NERON_TASK_WORKER_ENABLED=true|false
NERON_TASK_MAX_CONCURRENT=2
NERON_TASK_WORKER_POLL_SECONDS=0.25
```

The worker is disabled by default. The test suite explicitly keeps it
disabled unless a test constructs an enabled scheduler. Shutdown cancels and
awaits the worker and its active task set.

`run_worker_once()` is the controlled execution entry point used by tests and
can also be used by diagnostics.

## Priorities

Ready tasks are selected by:

1. priority: `critical`, `high`, `medium`, `low`;
2. oldest `created_at`.

Dependencies and retry delays are resolved before priority selection.

## Retry

Each task persists:

- `max_retries`;
- `retry_count`;
- `retry_delay_seconds`.

After a retryable failure, the task returns to `queued` and stores
`retry_not_before` plus `last_retry_error` in metadata. The worker continues
processing other tasks instead of sleeping for that retry.

Structural errors such as missing tools, unsafe tools, missing slugs, or an
unsupported task kind fail immediately.

## Tool Result Propagation

For each completed dependency, the scheduler merges `result.data` into the
next task payload. It also exposes the complete dependency results under
`dependency_results`.

The log workflow is:

```text
neron_log_reader_tool
  -> neron_log_error_filter_tool
  -> neron_log_summary_tool
```

The final result contains:

- `error_count`
- `severity`
- `components`
- `excerpt`
- `recommendation`

The Capability Resolver creates this chain for natural log-analysis requests
and stores the task IDs in capability and goal metadata. It also creates a
final composite task depending on the summary step and returns:

- `task_id`: first task in the chain;
- `scheduler_task_ids`: all tool tasks;
- `composite_task_id`: final observable workflow result.

When the worker is enabled, the chain starts asynchronously after enqueueing.
Telegram receives its immediate response without waiting for execution.

## API

Authenticated endpoints:

```http
GET  /tasks
GET  /tasks/{task_id}
POST /tasks/{task_id}/run
POST /tasks/{task_id}/cancel
```

Additional scheduler endpoints:

```http
GET  /tasks/status
GET  /tasks/running
GET  /tasks/next
POST /tasks/next/start
GET  /tasks/schema
```

## V2 Limits

- There is no cron expression or future `scheduled_for` timestamp.
- Retry delay is fixed per task; exponential backoff is not implemented.
- Interrupted tasks require an explicit decision to recreate or resume; V2
  does not automatically replay possibly non-idempotent work.
- Leases, distributed workers, process-level claiming, and multi-node
  execution are not implemented.
- Cancellation stops persisted scheduling. Cooperative cancellation inside a
  tool or agent execution is deferred.
