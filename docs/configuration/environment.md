# NeronOS v4.1 environment audit

Scope: full repository scan excluding `venv` and `.git`. Patterns checked:
`os.getenv`, `os.environ[...]`, `os.environ.get`, `getenv`, `BaseSettings`,
`dotenv`, `pydantic-settings`, `load_dotenv`, `environ[]`, shell expansions,
systemd `Environment` and `EnvironmentFile`.

No `BaseSettings`, `load_dotenv()` or `pydantic-settings` based settings class is
used by application code. `python-dotenv` appears only as a dependency.

## Variables

| Variable | Required | Default | Used in | Scope | Role |
| --- | --- | --- | --- | --- | --- |
| `ANTHROPIC_API_KEY` | Required only for Claude provider | empty | `server/llm/providers/claude.py` | `ClaudeProvider.__init__` | Authenticates calls to Anthropic Claude. |
| `AUDIO_MAX_SIZE_MB` | Optional | `10` | `server/core/config.py` | `Config` | Maximum STT audio upload size. |
| `CORS_ORIGINS` | Optional | localhost and Tailnet origins | `server/core/config.py` | `Config` | Comma separated CORS origins. |
| `DOCTOR_API_KEY` | Optional, recommended in production | empty | `server/modules/health/config.py`, `neron.yaml` declaration | `Config.__init__` | Doctor API authentication key. |
| `FORCE_COLOR` | Optional | empty | `server/agents/builtin/base_agent.py` | `get_logger` | Forces colored console logs when set to `1`. |
| `HA_ENABLED` | Optional | `false` | `server/core/config.py` | `Config` | Enables Home Assistant integration. |
| `HA_TIMEOUT` | Optional | `10.0` | `server/core/config.py` | `Config` | Home Assistant HTTP timeout. |
| `HA_TOKEN` | Required when HA is enabled | empty | `server/core/config.py`, consumed through `settings` by `server/agents/builtin/automation/ha_agent.py` | `Config` | Home Assistant bearer token. |
| `HA_URL` | Optional | `http://homeassistant.local:8123` | `server/core/config.py`, consumed by HA agent | `Config` | Home Assistant base URL. |
| `LLM_TIMEOUT` | Optional | `120` | `server/core/config.py` | `Config` | Core LLM timeout setting. |
| `LOG_LEVEL` | Optional | `INFO` | `server/core/config.py` | `Config`, `_validate_config` | Core application log level. |
| `NERON_ACTION_HISTORY_PATH` | Optional | `${NERON_DATA_DIR}/action_history.jsonl` | `server/core/api/action_history_routes.py`, `server/modules/autonomous/run_cognitive_loop.py`, `server/modules/cognitive/action_executor.py` | module constants | Action history JSONL path. |
| `NERON_AGENT_PROPOSALS_PATH` | Optional | `${NERON_DATA_DIR}/agent_creator_proposals.jsonl` | `server/agents/factory/agent_creator.py` | module constant | Agent proposal store path. |
| `NERON_API_KEY` | Required in production | `changez_moi` or empty depending component | `server/core/config.py`, `server/common/cli.py`, `server/common/registry/models.py`, `server/core/providers/llm/provider.py`, `server/llm/api/routes.py`, `neron.yaml` declaration | `Config`, registry, LLM routes | Shared internal API key. |
| `NERON_BRANCH` | Optional | `master` | `system/scripts/install.sh` | installer script | Git branch selected by install script. |
| `NERON_CODEX_BIN` | Optional | empty, auto-detect | `server/modules/evolution/codex_runner.py` | `resolve_codex_bin` | Codex executable override. |
| `NERON_CODEX_DRY_RUN` | Optional | unset/false | `server/modules/evolution/codex_runner.py` | `CodexRunner.__init__` | Runs evolution Codex jobs in dry-run mode when `1`. |
| `NERON_CODEX_TIMEOUT` | Optional | `1800` | `server/modules/evolution/codex_runner.py` | `CodexRunner.__init__` | Codex job timeout in seconds. |
| `NERON_CONFIG` | Optional | `${NERON_ROOT}/neron.yaml` | `server/common/paths.py`, systemd units | module constant | Path to central YAML config. |
| `NERON_CORE_HOST` | Optional | `0.0.0.0` | `system/scripts/start.py`, `system/scripts/run-distributed.sh`, `system/config/network.env.example` | service launcher | Core bind host for launcher scripts. |
| `NERON_CORE_HTTP` | Optional | `8010` | `server/core/config.py` | `Config` | Core HTTP port used by FastAPI config. |
| `NERON_CORE_PORT` | Optional | `8010` | `system/scripts/start.py`, `system/scripts/run-distributed.sh`, `system/config/network.env.example` | service launcher | Core bind port for launcher scripts. |
| `NERON_CORE_URL` | Optional | `http://localhost:8010` | `server/common/cli.py`, `server/common/registry/models.py`, `system/config/network.env.example` | CLI and registry settings | Core API base URL. |
| `NERON_CRITIC_HISTORY_PATH` | Optional | `${NERON_DATA_DIR}/critic_history.jsonl` | `server/core/api/critic_history_routes.py`, `server/modules/cognitive/critic_engine.py` | module constants | Critic history JSONL path. |
| `NERON_DATA_DIR` | Optional | `${NERON_ROOT}/data` | `server/common/paths.py`, many storage modules via import | module constant | Runtime data root. |
| `NERON_DIR` | Optional | `${NERON_ROOT}` | `server/core/config.py` | module constant, `Config` | Legacy root used by memory and model paths. |
| `NERON_DOCTOR_AUTH_DEV_MODE` | Optional | false | `server/doctor/config.py` | `Config.__init__` | Enables doctor auth dev mode. |
| `NERON_EVOLUTION_RUN_TIMEOUT` | Optional | `1800` | `server/modules/evolution/supervisor.py` | `EvolutionSupervisor.__init__` | Evolution supervisor execution timeout. |
| `NERON_EVOLUTION_STATE_PATH` | Optional | `${NERON_DATA_DIR}/evolution_state.json` | `server/modules/evolution/storage.py` | module constant | Evolution state store path. |
| `NERON_GATEWAY_TIMEOUT_SECONDS` | Optional | `10` | `server/core/infrastructure/gateway.py` | module constant | Gateway request timeout. |
| `NERON_GENERATED_AGENTS_DIR` | Optional | production generated agents dir | `server/agents/factory/registry.py` | module constant | Generated agents directory. |
| `NERON_GOAL_HOST` | Optional | `0.0.0.0` | `system/scripts/start.py` | service launcher | Goal service bind host. |
| `NERON_GOAL_MAX_ITERATIONS` | Optional | `3` | `server/core/goal_engine/execution_loop.py` | `GoalExecutionLoop.__init__` | Maximum goal loop iterations. |
| `NERON_GOAL_PORT` | Optional | `8030` | `system/scripts/start.py` | service launcher | Goal service bind port. |
| `NERON_GOALS_PATH` | Optional | `${NERON_DATA_DIR}/goals_state.json` | `server/goal/goals/persistence.py` | module constant | Goal state path. |
| `NERON_HEARTBEAT_INTERVAL` | Optional | `30.0` | `server/common/registry/models.py` via `env_float` | `RegistrySettings.from_env` | Registry heartbeat interval. |
| `NERON_HOST` | Optional | gateway default host | `server/core/gateway/gateway.py` | `main` | Standalone gateway bind host. |
| `NERON_IDENTITY_PATH` | Optional | Obsidian identity markdown path | `server/common/paths.py`, `server/core/identity/loader.py`, `server/core/modules/identity/service.py`, systemd unit | module constants, `_identity_path` | Identity document path. |
| `NERON_LLM_HOST` | Optional | `0.0.0.0` | `system/scripts/start.py`, `system/scripts/run-distributed.sh` | service launcher | LLM service bind host. |
| `NERON_LLM_PORT` | Optional | `8765` | `system/scripts/start.py`, `system/scripts/run-distributed.sh` | service launcher | LLM service bind port. |
| `NERON_LLM_RETRY` | Optional | `2` | `server/core/config.py` | `Config.NERON_LLM` | Retry count for Neron LLM client config. |
| `NERON_LLM_TIMEOUT` | Optional | `30` | `server/core/config.py`, `server/core/providers/llm/provider.py` | `Config.NERON_LLM`, `LLMProvider.__init__` | Neron LLM HTTP timeout. |
| `NERON_LLM_URL` | Optional | `http://localhost:8765` | `server/core/config.py`, `server/core/providers/llm/provider.py`, `system/config/network.env.example` | LLM client config | Neron LLM provider base URL. |
| `NERON_LOG_LEVEL` | Optional | `INFO` | `server/agents/builtin/base_agent.py` | `get_logger` | Agent logger level. |
| `NERON_LOGS_DIR` | Optional | default logging path | `server/core/logging/setup.py` | module constant | Log directory override. |
| `NERON_MAX_HISTORY_TOKENS` | Optional | `8000` | `server/modules/sessions.py` | module constant | Session pruning token limit. |
| `NERON_MEMORY_HOST` | Optional | `0.0.0.0` | `system/scripts/start.py`, `system/scripts/run-distributed.sh` | service launcher | Memory service bind host. |
| `NERON_MEMORY_PORT` | Optional | `8040` | `system/scripts/start.py`, `system/scripts/run-distributed.sh` | service launcher | Memory service bind port. |
| `NERON_PLANS_PATH` | Optional | `${NERON_DATA_DIR}/plans.jsonl` | `server/goal/planning/storage.py`, systemd unit | module constant | Plan store path. |
| `NERON_PORT` | Optional | gateway default port | `server/core/gateway/gateway.py` | `main` | Standalone gateway bind port. |
| `NERON_PROJECT_ROOT` | Optional | `NERON_ROOT` or current directory | `server/goal/planning/executor.py`, `server/agents/factory/agent_manager.py`, `server/agents/factory/build_orchestrator.py` | constructors/module constants | Project root for planning and agent factory. |
| `NERON_PROJECTS_PATH` | Optional | `${NERON_DATA_DIR}/projects.json` | `server/goal/projects/manager.py` | module constant | Project store path. |
| `NERON_REGISTRY_STALE_INTERVAL_SECONDS` | Optional | `30` | `server/core/app.py` | `_registry_stale_loop` | Registry stale-service scan interval. |
| `NERON_REGISTRY_STALE_TIMEOUT_SECONDS` | Optional | `90` | `server/core/app.py` | `_registry_stale_loop` | Registry stale-service timeout. |
| `NERON_ROOT` | Optional | `/etc/neronOS` | `server/common/paths.py`, systemd units | module constant | Runtime root. |
| `NERON_SANDBOX_BACKEND` | Optional | `auto` | `server/core/runtime/sandbox/agent_sandbox.py` | `AgentSandbox.__init__` | Sandbox backend selector. |
| `NERON_SANDBOX_SYSTEMD_USE_SUDO` | Optional | `auto` | `server/core/runtime/sandbox/agent_sandbox.py` | `AgentSandbox.__init__` | Whether systemd sandbox calls use sudo. |
| `NERON_SECRETS_FILE` | Optional | `${NERON_ROOT}/secrets.env` | `server/common/paths.py`, `server/common/cli.py` | module constant, `_api_key` | Secrets file path used by CLI fallback. |
| `NERON_SERVER_DIR` | Optional | `${NERON_ROOT}/server` | `server/common/paths.py` | module constant | Server source directory. |
| `NERON_SERVICE_HOST` | Optional | per-service default | `server/common/registry/models.py`, `system/scripts/start.py`, `system/scripts/run-distributed.sh`, systemd units | `service_from_env`, launchers | Advertised service host in registry. |
| `NERON_SERVICE_PORT` | Optional | per-service default | `server/common/registry/models.py`, launchers, systemd units | `service_from_env`, launchers | Advertised service port in registry. |
| `NERON_SESSIONS_DIR` | Optional | `${NERON_DATA_DIR}/sessions` | `server/modules/sessions.py` | module constant | Session storage directory. |
| `NERON_STATE_DB` | Optional | `${NERON_DATA_DIR}/neron_state.sqlite3` | `server/core/storage/sqlite_store.py` | module constant | SQLite state database path. |
| `NERON_TASK_MAX_CONCURRENT` | Optional | `2` | `server/modules/scheduler/scheduler.py` | `TaskScheduler.__init__` | Task worker concurrency. |
| `NERON_TASK_WORKER_ENABLED` | Optional | `false` | `server/modules/scheduler/scheduler.py` | `TaskScheduler.__init__`, `_env_bool` | Enables background task worker. |
| `NERON_TASK_WORKER_POLL_SECONDS` | Optional | `0.25` | `server/modules/scheduler/scheduler.py` | `TaskScheduler.__init__` | Worker poll interval. |
| `NERON_TASKS_PATH` | Optional | `${NERON_DATA_DIR}/tasks.json` | `server/goal/system/task_manager.py` | module constant | Goal task store path. |
| `NERON_TOKEN` | Optional | unset | `server/core/gateway/gateway.py` | `main` | Standalone gateway token. |
| `NERON_WORKSPACE` | Optional | workspace path | `server/agents/factory/*`, `server/core/gateway/telegram_gateway.py`, `server/agents/builtin/communication/telegram_agent.py`, `server/agents/builtin/dev/code_agent/agent.py` | module constants | Workspace path used by agents. |
| `NERON_WORKSPACE_DIR` | Optional | `${NERON_ROOT}/workspace` | `server/common/paths.py` | module constant | Canonical workspace directory. |
| `NERON_WORLD_MODEL_DIR` | Optional | `${NERON_DATA_DIR}/world_model` | `server/modules/memory/world_model/store.py` | module constant | World-model memory store directory. |
| `NERON_WORLD_MODEL_STATE_PATH` | Optional | `${NERON_DATA_DIR}/world_model_state.json` | `server/modules/world_model/world_model.py` | module constant | World model state path. |
| `OLLAMA_HOST` | Optional | `http://localhost:11434` | `server/core/config.py` | `Config` | Ollama API base URL. |
| `OLLAMA_MODEL` | Optional | `llama3.2:1b` | `server/core/config.py` | `Config` | Default Ollama model. |
| `SEARXNG_MAX_RESULTS` | Optional | `5` | `server/core/config.py` | `Config` | Web search result count. |
| `SEARXNG_TIMEOUT` | Optional | `10.0` | `server/core/config.py` | `Config` | Web search timeout. |
| `SEARXNG_URL` | Optional | `http://localhost:8080` | `server/core/config.py`, consumed by web agent settings | `Config` | SearXNG base URL. |
| `SERVER_HOST` | Optional | `0.0.0.0` | `server/core/config.py` | `Config` | Core server bind host in config. |
| `STT_TIMEOUT` | Optional | `60` | `server/core/config.py` | `Config` | STT timeout. |
| `TELEGRAM_BOT_TOKEN` | Required when Telegram is enabled | empty | `server/core/config.py`, consumed by Telegram agent and watchdog agent | `Config` | Telegram bot token. |
| `TELEGRAM_CHAT_ID` | Required for Telegram notifications | empty | `server/core/config.py` | `Config` | Telegram chat id. |
| `TELEGRAM_ENABLED` | Optional | `false` | `server/core/config.py` | `Config` | Enables Telegram bot. |
| `TTS_ENGINE` | Optional | `pyttsx3` | `server/core/config.py` | `Config` | TTS engine. |
| `TTS_LANGUAGE` | Optional | `fr` | `server/core/config.py` | `Config` | TTS language. |
| `TTS_MAX_CHARS` | Optional | `1000` | `server/core/config.py` | `Config` | TTS max input length. |
| `TTS_RATE` | Optional | `150` | `server/core/config.py` | `Config` | TTS speech rate. |
| `TWILIO_ACCOUNT_SID` | Required when Twilio is enabled | empty | `server/core/config.py`, consumed by `server/agents/builtin/communication/twilio_tool.py` | `Config` | Twilio account SID. |
| `TWILIO_AUTH_TOKEN` | Required when Twilio is enabled | empty | `server/core/config.py`, consumed by Twilio tool | `Config` | Twilio auth token. |
| `WATCHDOG_BOT_TOKEN` | Required when watchdog Telegram alerts are enabled | empty | `server/core/config.py`, consumed by watchdog agent | `Config` | Watchdog Telegram bot token. |
| `WATCHDOG_CHAT_ID` | Required when watchdog Telegram alerts are enabled | empty | `server/core/config.py` | `Config` | Watchdog alert chat id. |
| `WATCHDOG_CPU_ALERT` | Optional | `85` | `server/core/config.py` | `Config` | CPU alert threshold. |
| `WATCHDOG_CPU_TEMP_ALERT` | Optional | `75` | `server/core/config.py` | `Config` | CPU temperature alert threshold. |
| `WATCHDOG_DISK_ALERT` | Optional | `90` | `server/core/config.py` | `Config` | Disk alert threshold. |
| `WATCHDOG_ENABLED` | Optional | `false` | `server/core/config.py` | `Config` | Enables watchdog. |
| `WATCHDOG_INTERVAL` | Optional | `30` | `server/core/config.py` | `Config` | Watchdog interval. |
| `WATCHDOG_RAM_ALERT` | Optional | `85` | `server/core/config.py` | `Config` | RAM alert threshold. |
| `WHISPER_DOWNLOAD_ROOT` | Optional | `${NERON_DIR}/data/models` | `server/core/config.py` | `Config` | Whisper model cache directory. |
| `WHISPER_LANGUAGE` | Optional | `fr` | `server/core/config.py` | `Config` | Whisper language. |
| `WHISPER_MODEL` | Optional | `base` | `server/core/config.py` | `Config` | Whisper model. |

## Declared but not effectively resolved

These names are declared in `neron.yaml` or scripts, but the current core
configuration loader does not resolve the `*_env` indirection for them.

| Variable | Where declared | Status |
| --- | --- | --- |
| `HOMEASSISTANT_TOKEN` | `neron.yaml`, `system/scripts/ha.sh` comment/use | `server/core/config.py` reads `HA_TOKEN`, not `HOMEASSISTANT_TOKEN`. |
| `NEWS_API_KEY` | `neron.yaml`, `server/agents/builtin/io/news_agent.py` docstring | `Config` has no `NEWS_API_KEY`; news agent reads `settings.NEWS_API_KEY` and therefore gets empty default. |
| `TWILIO_FROM_NUMBER` | `neron.yaml` | `Config` reads YAML key `twilio.from_number` or env `TWILIO_FROM` is not configured as a fallback; `_env` key is ignored. |
| `TWILIO_TO_NUMBER` | `neron.yaml` | `Config` reads YAML key `twilio.to_number`; `_env` key is ignored. |

## Test-only variables

The following are set or read only by tests and are not included as production
secrets: `NERON_TEST_ROOT`, `NERON_MEMORY_DIR`.

## Anomalies

- `secret.env` was requested, but no `/etc/neronOS/secret.env` was present.
- Deployment files mostly reference `secrets.env` plural, not `secret.env`.
- Environment file paths are inconsistent: `/etc/neron/secrets.env`,
  `/etc/neronOS/secrets.env`, and the requested `/etc/neronOS/secret.env`.
- `system/scripts/start.py` uses root `/etc/neron`, while this checkout and
  most systemd units use `/etc/neronOS`.
- Naming duplicates exist for similar concepts: `NERON_CORE_HTTP` vs
  `NERON_CORE_PORT`, `LOG_LEVEL` vs `NERON_LOG_LEVEL`, `LLM_TIMEOUT` vs
  `NERON_LLM_TIMEOUT`, `HA_TOKEN` vs `HOMEASSISTANT_TOKEN`, YAML
  `twilio.from_number` vs `TWILIO_FROM_NUMBER`, and YAML `twilio.to_number` vs
  `TWILIO_TO_NUMBER`.
- `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` have env fallbacks, but
  `TWILIO_FROM` and `TWILIO_TO` do not; only YAML keys are read.
- `NEWS_API_KEY` and `WEATHER_DEFAULT_CITY` are documented by agents/YAML, but
  not exposed by `server/core/config.py`.
- `NERON_MEMORY_URL`, `NERON_DOCTOR_URL`, and `NERON_HOMEASSISTANT_URL` appear in
  `system/config/network.env.example`, but no application code read was found.
- Several variables are duplicated across modules as direct `os.getenv` calls
  instead of a single typed settings object.

## Hardcoded secret scan

No real hardcoded secret value was found by pattern scan for common API key,
token, bearer, GitHub, OpenAI-style, or Telegram-token formats. Remaining hits
are placeholders, examples, shell variable expansions, or test keys.
