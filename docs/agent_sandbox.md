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

## V2: systemd-run

`NERON_SANDBOX_BACKEND` accepts `auto`, `python`, or `systemd` and defaults to
`auto`. Automatic selection uses `systemd-run` only when the binary is present
and the dedicated `neron-agent` account exists. Otherwise it keeps the existing
Python backend, including `bubblewrap` when usable.

Create the account only after administrator review:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin neron-agent
```

The account must be able to traverse `/etc/neron` and read the runner and agent
dependencies. It needs write access only to `/etc/neron/workspace`; ownership
and ACL changes remain an explicit administrator operation.

The systemd transient unit runs with:

- `NoNewPrivileges=yes`, `PrivateTmp=yes`, `ProtectSystem=strict`, and
  `ProtectHome=yes`;
- write access restricted to `/etc/neron/workspace`;
- `MemoryMax=256M`, `CPUQuota=50%`, and `RuntimeMaxSec=30`;
- address families restricted to `AF_UNIX`;
- `SystemCallFilter=@system-service`;
- the fixed `neron-agent` uid (`DynamicUser=no`).

Example configuration:

```bash
export NERON_SANDBOX_BACKEND=auto
export NERON_SANDBOX_SYSTEMD_USE_SUDO=auto
```

`NERON_SANDBOX_SYSTEMD_USE_SUDO` accepts `true`, `false`, or `auto` and
defaults to `auto`. `true` always prefixes the transient-unit command with
`sudo -n`; `false` calls `systemd-run` directly; `auto` uses sudo when the
Néron process is non-root. Before selecting systemd with sudo, the adapter
checks the exact allowed command non-interactively with:

```bash
sudo -n /usr/bin/systemd-run --version
```

For a non-root `neron-core`, sudoers can grant only that executable:

```sudoers
neron ALL=(root) NOPASSWD: /usr/bin/systemd-run
```

Diagnostics are returned on every sandbox result as `backend_used`,
`isolation_level`, `systemd_available`, `user_available`, and
`fallback_reason`, plus `sudo_used`, `sudo_available`, `sudo_error`, and
`systemd_run_path`. Projects expose `sandbox_backend`,
`sandbox_isolation_level`, and `sandbox_status`.

Host diagnostics:

```bash
command -v systemd-run
getent passwd neron-agent
systemctl is-system-running
systemd-run --version
sudo -n /usr/bin/systemd-run --version
```

An explicit `systemd` configuration fails closed when the binary, account,
required sudo authorization, or unit launch is unavailable. Automatic mode
falls back to the Python backend when systemd or required sudo authorization
is unavailable during backend selection. It does not re-run an agent with
weaker isolation after a systemd execution failure.

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
events in the Goal Execution Engine. V2 also records
`sandbox_backend_selected`, `sandbox_systemd_started`,
`sandbox_systemd_failed`, and `sandbox_fallback_python`.

## Remaining Limits

- Python audit hooks are a defense for generated Python agents, not a kernel
  security boundary. Native code loaded through `ctypes` could bypass them.
- The systemd backend depends on a running system manager and authorization to
  create a transient unit for `neron-agent`.
- Read access outside the workspace remains available because generated agents
  may import Néron core modules. Secrets must not be exposed to generated code
  solely through filesystem permissions.
- Memory limits use `RLIMIT_AS`; behavior can vary for native extensions that
  reserve large virtual address ranges.
