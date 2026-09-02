> **ARCHIVE — NE FAIT PLUS FOI.**
>
> Document de la Phase 4, conservé pour l'historique. Il décrit une
> architecture systemd entièrement remplacée depuis : les unités
> `neron-core.service`, `neron-llm.service`, `neron-doctor.service`,
> `neron-web.service`, `neron-watchdog.service`, `neron-vocal.service`,
> `neron-stt.service` et `neron-kula.service` n'existent plus. Les services
> métier passent aujourd'hui par le template `neron@<noeud>.service`.
>
> Il affirme par ailleurs que `neron-cognitive-loop`, `neron-self-model-loop`
> et `neron-world-model-loop` sont désactivées : les trois sont en réalité
> actives.
>
> Référence courante : [Architecture de référence](../architecture/neronos-architecture.md).

---

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
