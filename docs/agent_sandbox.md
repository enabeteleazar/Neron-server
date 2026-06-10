# Agent Sandbox

## Purpose

Every generated agent must pass an isolated execution barrier before
`RuntimeGovernor`, registry promotion, and runtime loading.

`core/runtime/sandbox/agent_sandbox.py` is the shared entry point for:

- generated-agent pytest execution;
- business validation;
- a final workspace-agent execution check before promotion.

The existing post-registry runtime verification remains in place. It verifies
that the promoted agent can be discovered, loaded, and executed by the real
runtime; it does not replace the pre-promotion sandbox.

## Isolation Strategy

The sandbox starts a dedicated Python subprocess with:

- a fixed working directory at `/etc/neron/workspace` (or the configured
  project workspace);
- a minimal environment containing only `HOME`, locale, `PATH`,
  `PYTHONDONTWRITEBYTECODE`, and `TMPDIR`;
- a wall-clock timeout that kills the complete process group;
- CPU, address-space, file-size, open-file, and process-count limits;
- network and child-process denial;
- write access restricted to the workspace.

When unprivileged user namespaces are available, `bubblewrap` provides a
read-only root filesystem, a writable workspace bind mount, a private `/tmp`,
and no network namespace.

When `bubblewrap` is unavailable or forbidden by the host kernel, the sandbox
falls back to Python audit hooks. The fallback blocks Python file mutations
outside the workspace, subprocess creation, and network operations. The
reported `isolation` field is `bubblewrap` or `python_audit`.

## Pipeline And States

The pre-promotion order is:

```text
validation
compile
sandbox_started
  pytest
  business validation
  isolated verification
sandbox_passed
runtime_governor
registry
runtime verification
```

On any sandbox failure:

- project `status` becomes `failed`;
- `sandbox_status` becomes `failed`;
- `registry_status` remains `not_registered`;
- `runtime_status` becomes `not_available`;
- registry promotion is not attempted.

Tracked goals record `sandbox_started`, `sandbox_passed`, or `sandbox_failed`
events in the Goal Execution Engine.

## Remaining Limits

- Python audit hooks are a defense for generated Python agents, not a kernel
  security boundary. Native code loaded through `ctypes` could bypass them.
- Strong filesystem and network isolation therefore depends on functional
  unprivileged user namespaces and `bubblewrap`.
- Read access outside the workspace remains available because generated agents
  may import Néron core modules. Secrets must not be exposed to generated code
  solely through filesystem permissions.
- Memory limits use `RLIMIT_AS`; behavior can vary for native extensions that
  reserve large virtual address ranges.
