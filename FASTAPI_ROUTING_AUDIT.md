# FastAPI routing audit

## Summary
The Core app now registers routers without re-including the same router object twice, and the legacy `/tasks/legacy*` task routes are no longer present.

## Findings
- The main duplicate issue was the legacy task router from `core.api.task_routes` registering `/tasks` and `/tasks/{task_id}` alongside the newer scheduler router from `modules.scheduler.routes`.
- The `/goals` path is intentionally shared by two distinct endpoints: `GET /goals` and `POST /goals`.
- `/agents/registry/scan` is intentionally registered as both `GET` and `POST`.
- `/registry/services/{service_name}` is intentionally registered as both `GET` and `DELETE`.
- The remaining duplicate-path entries are therefore method/path pairs with different methods, not duplicate registrations of the same method/path pair.

## Route inventory

| Route | Module | Statut | Doublon | Peut être supprimée |
| --- | --- | --- | --- | --- |
| `/tasks` | `modules.scheduler.routes` | Actif | Oui (avec `/tasks` legacy) | Non |
| `/tasks/{task_id}` | `modules.scheduler.routes` | Actif | Oui (avec legacy task router) | Non |
| `/tasks/legacy` | `core.api.task_routes` | Legacy | Oui | Oui |
| `/tasks/legacy/{task_id}` | `core.api.task_routes` | Legacy | Oui | Oui |
| `/goals` | `goal.goals.routes` | Actif | Oui (GET/POST) | Non |
| `/agents/registry/scan` | `goal.projects.routes` | Actif | Oui (GET/POST) | Non |
| `/registry/services/{service_name}` | `core.app` | Actif | Oui (GET/DELETE) | Non |

## Actions taken
- Removed the legacy task router registration from the main router list in `server/core/app.py`.
- Added a guard so the same router object is not included more than once.
- Kept the planner and other functional routers active.

## Verification
Executed:

```bash
PYTHONPATH=/etc/neronOS/server python3 - <<'PY'
import importlib
from collections import defaultdict
mod = importlib.import_module('core.app')
app = mod.app
routes = [r for r in app.routes if hasattr(r, 'path') and getattr(r, 'path', None)]
paths = [r.path for r in routes]
by_path = defaultdict(list)
for r in routes:
    by_path[r.path].append(r)
print('Total routes:', len(routes))
print('Unique paths:', len(set(paths)))
print('Duplicate paths:', [(p, len(v)) for p,v in by_path.items() if len(v) > 1])
print('Legacy task paths present:', [p for p in ['/tasks/legacy', '/tasks/legacy/status', '/tasks/legacy/{task_id}'] if p in by_path])
PY
```

Observed result:
- Total routes: 132
- Unique paths: 129
- Duplicate paths: `/goals`, `/agents/registry/scan`, `/registry/services/{service_name}`
- Legacy task paths present: `[]`
