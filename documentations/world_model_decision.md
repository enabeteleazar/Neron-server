# Decision WorldModel

Date: 2026-06-02

## Decision

Le WorldModel officiel au runtime est:

- module: `core.world_model.world_model`
- boucle: `core.world_model.world_model_loop`
- service: `neron-world-model-loop.service`
- routes FastAPI: `core.api.world_model_routes`
- endpoints publics actuels: `/world-model/context`, `/world-model/status`, `/world-model/summary`

## Surface de compatibilite

`core.memory.world_model.*` est conserve comme surface historique enrichie:

- builder de snapshot
- store SQLite/cache
- API historique `world_model_router`
- tests unitaires du builder

Cette surface n'est pas incluse dans `core.app` aujourd'hui. Elle ne doit pas devenir une deuxieme source de verite runtime sans decision explicite.

## Statut des fichiers

- `core/world_model/world_model.py`: actif
- `core/world_model/world_model_loop.py`: actif
- `core/api/world_model_routes.py`: actif
- `core/memory/world_model/builder.py`: compatibilite/test
- `core/memory/world_model/store.py`: compatibilite
- `core/memory/world_model/api.py`: legacy-compatible, non inclus par `core.app`
- `core/memory/world_model/world_model.py`: compatibilite pour le watchdog historique

## Regle future

Avant toute fusion ou suppression, prouver:

1. quelle surface est appelee par systemd;
2. quelle surface est incluse par FastAPI;
3. quels tests couvrent les comportements conserves.

