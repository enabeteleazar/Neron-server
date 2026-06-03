# Resolution des Constats Restants

Date: 2026-06-02

## Constats traites

### 1. Endpoints internes publics

Routes protegees avec `X-API-Key` via `core.api.auth.verify_api_key`:

- `/planner/*`
- `/tasks/*`
- `/evolution/*`
- `/projects/*`
- `/agents`
- `/agents/build`

Endpoints publics conserves:

- `/`
- `/health`
- `/status`
- `/docs`
- `/goals/active`
- `/world-model/status`
- `/self-model/status`

Tests ajoutes:

- `tests/test_internal_endpoint_auth.py`

### 2. Couplage Telegram / orchestrateurs

Decision:

- Telegram transmet des commandes metier a `NeronCommandDispatcher`.
- `core.agents.communication.telegram_agent` ne reference plus directement `core.goals.goal_orchestrator` ni `core.evolution.supervisor`.

Fichiers ajoutes:

- `core/orchestration/command_dispatcher.py`
- `core/orchestration/__init__.py`
- `docs/telegram_architecture.md`
- `tests/test_command_dispatcher.py`

### 3. WorldModel et surfaces Telegram

Decision WorldModel:

- officiel runtime: `core.world_model.world_model`
- routes officielles: `core.api.world_model_routes`
- boucle officielle: `core.world_model.world_model_loop`
- compatibilite legacy: `core.memory.world_model.*`

Decision Telegram:

- surface principale: `core.agents.communication.telegram_agent`
- compatibilite control-plane: `core.gateway.telegram_gateway`
- legacy documentaire: `core.agents.communication.telegram_patch`

Fichiers ajoutes:

- `docs/world_model_decision.md`
- `docs/telegram_surface_decision.md`
- `tests/test_runtime_surface_decisions.py`

### 4. Service systemd legacy

Decision:

- service principal officiel: `neron-core.service`
- `deploy/systemd/neron.service` est legacy et ne doit pas etre installe.
- `scripts/server.sh` cible maintenant `neron-core.service`.
- `neron-watchdog.service` n'existe pas sur la machine auditee; le watchdog est lance par `neron-core`.

Fichiers ajoutes/modifies:

- `docs/systemd_services.md`
- `deploy/systemd/neron.service`
- `scripts/server.sh`
- `tests/test_systemd_services.py`

### 5. Compatibilite legacy modules

La validation demandait `compileall core modules scripts`, mais le package top-level `modules` n'existait pas. Un wrapper de compatibilite `modules.* -> core.modules.*` a ete ajoute.

Fichiers ajoutes:

- `modules/__init__.py`
- `modules/scheduler.py`
- `modules/sessions.py`
- `modules/skills.py`
- `modules/autonomous/__init__.py`
- `modules/autonomous/scheduler.py`
- `tests/test_legacy_modules_compat.py`

### 6. Alias SelfModel status

Ajout de `/self-model/status` dans le router inclus par `core.app`, sans modifier les endpoints existants.

Fichiers modifies:

- `core/api/self_model_context_routes.py`
- `tests/test_goal_agent_creation_flow.py`

## Commits locaux

- `8af7116 fix(api): protect internal orchestration endpoints`
- `11aa1ac refactor(telegram): decouple command handling from orchestrators`
- `cf738b0 refactor(core): clarify world model and telegram runtime surfaces`
- `7d38927 chore(systemd): mark legacy service definition and document active units`
- `986e2d5 fix(core): keep legacy modules imports compatible`
- `735bd4c fix(api): expose self model status alias`

## Commandes executees

- `venv/bin/python -m pytest -q`
- `venv/bin/python -m compileall core modules scripts`
- `git diff --check`
- `sudo systemctl restart neron-core`
- verification HTTP locale des endpoints:
  - `GET / -> 200`
  - `GET /health -> 200`
  - `GET /self-model/status -> 200`
  - `GET /world-model/status -> 200`
  - `GET /goals/active -> 200`
  - `GET /planner/status -> 200` avec `X-API-Key`
  - `GET /evolution/status -> 200` avec `X-API-Key`
- `git status --short`
- `git log --oneline -5`

## Resultats

- Tests: `272 passed, 3 warnings`
- Compileall: OK
- Diff check: OK
- Endpoints live: OK apres redemarrage de `neron-core`
- Push: non effectue

## Risques restants

- `/goals/*`, `/code-awareness/*` et `/runtime/governor/policy` restent publics par compatibilite, hors scope du chantier d'auth cible.
- Le control-plane Telegram gateway ne doit pas etre lance avec le meme token que le bot principal.
- Les wrappers legacy `modules.*` doivent rester transitoires; les nouveaux imports doivent utiliser `core.modules.*`.
- `core.memory.world_model.*` reste une surface historique importable, mais ne doit pas redevenir source de verite runtime sans decision explicite.

