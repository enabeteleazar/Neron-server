# Audit Securite

Date: 2026-06-02

## Surface d'execution

Subprocess identifies:

- `core/evolution/codex_runner.py`: lance Codex, tests et git via commandes listees, sans `shell=True`, avec timeout.
- `core/agent_factory/build_orchestrator.py`: lance tests/validation; a garder sous gouvernance runtime.
- `core/planning/executor.py`: execute pytest pour validation de plan.
- `core/service_core/service_manager.py`: appelle `systemctl is-active` apres autorisation RuntimeGovernor.
- `core/world_model/world_model.py` et `core/self_model/self_model.py`: sondes systeme via commandes bornees.
- `core/agents/communication/telegram_agent.py` et `core/gateway/telegram_gateway.py`: `/run` execute un fichier Python du workspace avec timeout.
- `core/agents/dev/code_agent/agent.py`: execution de code en subprocess isole et timeout.
- `core/runtime/tools/system/journal_tool.py`: `journalctl` limite a une liste blanche de services.

Constat: les usages critiques emploient majoritairement des listes d'arguments et des timeouts. Aucun `shell=True` n'a ete detecte dans `core`.

## Endpoints sensibles

Proteges par `X-API-Key`:

- `/ha/reload`
- `/memory`
- `/personality/state`
- `/personality/history`
- `/personality/reset`
- `/nlp/parse`
- `/input/text`
- `/input/stream`
- API historique `core/memory/world_model/api.py`

Endpoints operationnels proteges depuis le chantier de resolution:

- `/planner/*`
- `/tasks/*`
- `/evolution/*`
- `/projects/*`
- `/agents` et `/agents/build`

Endpoints operationnels encore publics:

- `/goals/*`
- `/code-awareness/*`
- `/runtime/governor/policy`

Risque residuel: si `neron-core` est expose hors reseau de confiance, les endpoints encore publics peuvent exposer des informations internes. Compatibilite API conservee pour ces surfaces non ciblees par le chantier.

## Secrets et API keys

- Configuration centralisee dans `core/config.py`.
- Warning si `API_KEY == changez_moi`.
- `core/evolution/codex_runner.py` redacte tokens, API keys, bearer tokens et mots de passe dans les logs/resultats Codex.
- Scripts shell d'installation Telegram/Home Assistant manipulent tokens en clair pendant configuration interactive; ne pas journaliser leurs sorties.

## Acces fichiers

- Donnees runtime sous `/etc/neron/data`.
- Logs par defaut sous `/var/log/neron`.
- Correction appliquee: fallback logging vers `/tmp/neron/logs` quand `/var/log/neron` n'est pas inscriptible et qu'aucun `NERON_LOGS_DIR` explicite n'est fourni.
- Code awareness contient des garde-fous de chemin (`core/code_awareness/security.py`).

## Risques residuels

- Les endpoints internes ne partagent pas tous la meme politique d'authentification.
- Les commandes Telegram `/run`, `/fix`, `/review` restent puissantes par design; elles doivent rester reservees a l'utilisateur autorise.
- Couplage Telegram/orchestration pouvant compliquer la gestion d'erreur en cas d'import circulaire futur.
- Multiples dossiers hors core (`client/node_modules`, `client_vocal/node_modules`, `venv`, backups) augmentent le bruit des audits; les scans de securite doivent les exclure explicitement.
