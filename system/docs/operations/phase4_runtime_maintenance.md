# Maintenance runtime Phase 4

## Services actifs

- `neron-core.service` : API principale Néron Core
- `neron-llm.service` : microservice LLM
- `neron-doctor.service` : diagnostic système
- `neron-web.service` : interface web Néron
- `neron-watchdog.service` : surveillance et alertes
- `neron-homeassistant.service` : Home Assistant
- `ollama.service` : fournisseur LLM local

## Services reclassés / désactivés

- `neron-dashboard.service` : remplacé par `neron-web.service`
- `neron-cognitive-loop.service` : désactivé, à réévaluer avec Goal/Watchdog
- `neron-self-model-loop.service` : désactivé, logique partiellement intégrée au Core
- `neron-world-model-loop.service` : désactivé, logique à réévaluer
- `neron-vocal.service` : désactivé, à migrer plus tard
- `neron-stt.service` : désactivé, à migrer plus tard
- `neron-kula.service` : désactivé, legacy
