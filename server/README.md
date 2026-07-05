## Cerveau -> Backend de Neron

### Démarrage systemd

Le serveur principal est l'application ASGI `core.app:app`. Le répertoire
`core` est un sous-module Git et doit être initialisé avec les autres services
avant le premier démarrage :

```bash
cd /etc/neronOS
git submodule update --init server/core server/goal server/llm server/doctor
sudo systemctl daemon-reload
sudo systemctl restart neronOS
curl -s http://127.0.0.1:8010/health
```

L'unité utilise `/etc/neronOS/server` comme `WorkingDirectory` et comme
`PYTHONPATH`, avec la commande suivante :

```text
/etc/neronOS/venv/bin/python -m uvicorn core.app:app --host 0.0.0.0 --port 8010
```

Les chemins runtime sont centralisés dans `common.paths`. `NERON_ROOT`
vaut `/etc/neronOS` par défaut et `NERON_CONFIG` vaut
`$NERON_ROOT/neron.yaml`; les deux restent surchargeables par environnement.
