# Health Center de Néron

Health Center est la couche de santé normalisée de Néron OS. Il remplace progressivement le rôle historique de Doctor sans supprimer les anciens imports ni modifier brutalement les formats publics.

## Responsabilités

| Module | Responsabilité |
| --- | --- |
| **Health Center** | Collecter l'état réel du système, vérifier les services critiques, agréger les événements récents, produire un snapshot, des diagnostics et des recommandations. |
| **Doctor** | Façade de compatibilité pour les anciens imports et scripts de diagnostic. Il peut déléguer au Health Center. |
| **SelfModel** | Interpréter l'état interne de Néron à partir du Health Center : “qui suis-je et dans quel état interne suis-je ?”. |
| **WorldModel** | Interpréter l'état de l'environnement d'exécution à partir du Health Center : ressources, événements récents, recommandations. |
| **Watchdog** | Surveiller activement et relancer les services. Il ne devient pas le moteur de diagnostic complet. |
| **Event Bus** | Transport append-only JSONL des signaux système, agent, LLM, watchdog et santé. |

## API

### `GET /health`

Endpoint historique conservé sans changement destructif. La réponse reste compatible :

```json
{
  "status": "healthy",
  "version": "..."
}
```

### `GET /health-center/status`

Nouveau endpoint stable du Health Center :

```json
{
  "status": "stable",
  "services": {},
  "resources": {},
  "diagnostics": [],
  "recommendations": [],
  "events": [],
  "timestamp": "..."
}
```

`status` vaut actuellement `stable`, `degraded` ou `critical` selon les diagnostics générés.

### Adaptateurs SelfModel et WorldModel

Deux endpoints de compatibilité sont disponibles :

- `GET /self-model/status`
- `GET /world-model/status`

Ils consomment Health Center au lieu de dupliquer la collecte système.

## Événements publiés par Health Center

Health Center publie ces événements quand les conditions sont observées :

- `health.snapshot.created`
- `health.status.changed`
- `health.service.unreachable`
- `health.service.recovered`
- `health.resource.warning`
- `health.resource.critical`
- `health.diagnostic.created`

## Événements écoutés / agrégés

Health Center garde les événements pertinents dans le snapshot quand ils apparaissent dans le bus JSONL :

- `system.service.started`
- `system.service.stopped`
- `system.service.error`
- `agent.execution.failed`
- `llm.provider.error`
- `watchdog.restart.performed`
- `goal.changed`

## Compatibilité événementielle

Le bus Health Center écrit par défaut dans `data/events.jsonl`, ou dans le chemin défini par `NERON_EVENTS_JSONL` / `HEALTH_EVENTS_PATH`. Il tente aussi de refléter les événements vers la table SQLite historique du Watchdog via `watchdog_agent.log_event()` quand elle est disponible.

## Migration progressive

- Ne pas supprimer Doctor : garder `modules.external.doctor.run_diagnostics()` comme façade.
- Déplacer progressivement la collecte système du SelfModel et du WorldModel vers Health Center.
- Garder Watchdog concentré sur la relance automatique.
- Ajouter les nouveaux diagnostics dans `core/health/diagnostics.py` sans changer le contrat public de `/health`.
