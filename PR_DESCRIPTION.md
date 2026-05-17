Title: Refactor to JARVIS-style architecture (server/core, agents/internal, modules/external)

Description:
This PR reorganizes the project into a JARVIS-style autonomous assistant architecture:
- server/core: orchestrator, router, policy_engine, memory
- agents/internal: deterministic agents (timer, searchx, review, code_tools)
- modules/external: LLM and external integrations (llm, doctor, copilot)
- Adds robust YAML shim (fallback if PyYAML not available), constraints, bootstrap script, and GitHub Actions CI for tests.
- Fixes: LLM manager provider timeout compatibility; test dependency adjustments; created llm pyproject.

Notes:
- Sensitive secrets found in server/neron.yaml MUST be rotated and removed before merging.
- The bootstrap script requires sudo to install system build deps (build-essential, libyaml-dev).
- CI workflow installs system deps; adjust if runner privileges differ.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
