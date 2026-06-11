# Capability Resolver V2

## Purpose

Telegram is the current test transport for Néron's future voice interface. The
target pipeline is transport-independent:

```text
Telegram now / STT later
  -> text input
  -> Intent Router
  -> Capability Resolver
  -> direct answer, tool, agent, or supervised creation
  -> text response
  -> Telegram now / TTS later
```

Users do not need to know about `/goal`, Agent Creator, Codex, projects,
registry, sandbox, or runtime. Those components remain internal supervision
and execution mechanisms.

## Components

`core/capabilities/models.py` defines:

- `CapabilityRequest`: normalized transport-independent input;
- `CapabilityDecision`: routing choice and safety metadata;
- `CapabilityResult`: immediate or asynchronous user result;
- `Capability`: a registry entry from a tool, agent, project, or future
  external service.

The V2 understanding pipeline is split into explicit components:

- `rules.py`: high-confidence domain rules;
- `domain_classifier.py`: domain classification;
- `intent_extractor.py`: action extraction and durability detection;
- `matcher.py`: domain-first capability scoring;
- `decision_engine.py`: execution, creation, or conversation decision;
- `intent_provider.py`: asynchronous provider contract and current
  `RuleBasedIntentProvider`.

`LlmIntentProvider` is reserved as a future hook. V2 does not call an LLM.

`core/capabilities/router.py` remains the immediate safety and compatibility
layer.

`core/capabilities/registry.py` discovers:

- built-in tools;
- generated modules from `DynamicAgentRegistry`;
- completed builds from `ProjectManager`;
- capabilities registered at runtime.

`core/capabilities/resolver.py` matches, executes, or queues the selected
capability.

## Decisions

Supported decisions are:

- `direct_answer`
- `use_existing_tool`
- `use_existing_agent`
- `create_tool`
- `create_agent`
- `ask_human_validation`
- `reject`

The V2 analysis contract uses:

- `execute_tool`
- `execute_agent`
- `create_tool`
- `create_agent`
- `fallback_conversation`

The Resolver maps `execute_*` to the historical `use_existing_*` execution
contract so existing transports and tests remain compatible.

The authenticated debug endpoint exposes the V2 analysis without executing
anything:

```http
POST /capabilities/analyze
Content-Type: application/json

{"text": "Analyse les sauvegardes Néron"}
```

Unknown requests are not forced through this layer. The resolver returns
control to the existing intent and conversation pipeline when its heuristics
do not establish a useful decision.

## Tool And Agent Boundary

A tool is short-lived and deterministic: calculate, convert, read one value,
or perform one bounded action. Built-in examples include Easter dates,
Christmas countdowns, subnet calculations, and a point-in-time system
diagnostic.

An agent is durable: monitor, retain state, run periodically, alert, or
orchestrate several tools over time.

Generated deterministic modules are exposed as tools even when the current
builder stores them under `core/agents/generated`. Their metadata keeps
`creation_type=tool`. Durable generated modules remain agents.

## Missing Capabilities

Missing capabilities are queued asynchronously through the existing goal
execution stack:

```text
Capability Resolver
  -> GoalManager / GoalExecutionEngine
  -> GoalBackgroundRunner
  -> GoalOrchestrator
  -> AgentBuildOrchestrator
  -> validation
  -> Business Validation
  -> Agent Sandbox
  -> Runtime Governor
  -> Registry
  -> Runtime verification
```

The current builder still represents a generated tool with the agent module
contract. This is an implementation compatibility detail, not the user-facing
capability type.

Internal capability builds require a reliable Business Validation scenario.
They cannot pass with the legacy `generic_non_empty_response` fallback.
Generic responses are rejected before Registry promotion. Historical internal
projects validated by that fallback are excluded from capability matching and
must be rebuilt under the stricter policy.

The immediate response is intentionally short:

```text
Je m’en occupe. Je te reviens avec la réponse dès que c’est prêt.
```

The response metadata contains `request_id` and `goal_id`. Progress and the
final result can be recovered through:

```http
GET /capabilities/requests/{request_id}
GET /goal/{goal_id}/status
```

When the build is complete, `CapabilityResolver.get_result()` executes the
new runtime capability against the original user text and returns the business
answer. Automatic proactive Telegram notification is not implemented yet.

## Transport Rules

Telegram only sends `text`, `source_channel`, and `user_id` to `/input/text`.
It does not import the resolver, goal orchestrator, builder, registry, or
sandbox.

The voice endpoint already delegates its transcription to `text_input`, so it
uses the same resolver before TTS without a Telegram dependency.

Technical build fields remain in authenticated status APIs and debug metadata.
Normal user responses do not mention plan IDs, registry state, sandbox,
Codex, or build logs.

## Rule-Based Understanding

- domains: Christmas, Easter, weather, subnet, logs, backups, SQLite,
  systemd, agenda, and calendar;
- intents: analysis, summary, diagnostic, monitoring, calculation, creation,
  search, comparison, and notification;
- domain compatibility has more weight than generic lexical overlap;
- a known domain mismatch caps a capability score below the execution
  threshold;
- operational analysis without a relevant agent creates an agent;
- an existing agent with a missing declared tool requests tool creation;
- destructive or secret-related actions still require human validation.

This design allows a future asynchronous LLM provider to replace or augment
the rule provider without changing matching, decision, request, or result
contracts.
