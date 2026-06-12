# Services systemd Neron

Date: 2026-06-02

## Services officiels actuels

- `neron-core.service`: service principal API, lance `uvicorn core.app:app` sur le port 8010.
- `neron-self-model-loop.service`: boucle SelfModel, lance `python3 -m core.self_model.self_model_loop`.
- `neron-world-model-loop.service`: boucle WorldModel officielle, lance `python3 -m core.world_model.world_model_loop`.
- `neron-cognitive-loop.service`: boucle cognitive, lance `core/autonomous/run_cognitive_loop.py`.
- `neron-llm.service`: microservice LLM si installe.
- `neron-doctor.service`: service doctor si installe.

## Watchdog

Il n'existe pas d'unite `neron-watchdog.service` sur la machine auditee. Le watchdog est lance par `neron-core` via `core.app`:

- `start_watchdog()`
- `start_watchdog_bot()`

## Services legacy ou compatibilite

- `deploy/systemd/neron.service`: legacy. Ne pas installer. Ce fichier pointe vers `server.core.app:app`, ancien chemin non officiel.
- `neron.service`: un lien systemd historique peut exister dans `multi-user.target.wants`, mais aucune unite chargee n'a ete trouvee par `systemctl cat neron.service` pendant l'audit.
- `deploy/systemd/*`: variantes historiques restantes. Les cinq copies
  byte-identiques des unités critiques ont été supprimées; les unités
  officielles sont les fichiers `deploy/neron-*.service`.

## Scripts

- `scripts/install_systemd.sh` installe les unites officielles existantes depuis `deploy/`.
- `scripts/server.sh` cible `neron-core.service`.
- `deploy/neronctl` cible deja `neron-core.service`.

## Commandes utiles

```bash
systemctl status neron-core
systemctl status neron-self-model-loop
systemctl status neron-world-model-loop
systemctl status neron-cognitive-loop
journalctl -u neron-core -n 100 --no-pager
```

## Regle

Le service principal a utiliser est `neron-core.service`. Toute documentation ou script pointant vers `neron.service` doit etre considere comme legacy et corrige avant usage.
