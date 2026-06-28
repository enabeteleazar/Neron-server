# Phase 4 runtime maintenance

## Services systemd

Les services maintenus utilisent les chemins canoniques suivants :

- `neron-core`: `core.app:app`
- `neron-cognitive-loop`: `modules/autonomous/run_cognitive_loop.py`
- `neron-doctor`: `modules.health.app:app`
- `neron-self-model-loop`: `modules.self_model.self_model_loop`
- `neron-world-model-loop`: `modules.world_model.world_model_loop`
- `neron-dashboard`: `ui/dashboard/dist/index.cjs`
- `neron-vocal`: `ui/vocal/server.js`

Les unités utilisent `Restart=on-failure`, une temporisation de 10 secondes et
une limite de trois tentatives par minute. Une erreur persistante doit donc
laisser le service en état `failed` au lieu de provoquer une boucle infinie.

## Contexte LLM

Le contexte global et l'identité utilisent le document canonique :

`/etc/neron/memory/obsidian/identity/NERON.md`

Aucune copie `/etc/neron/NERON.md` n'est maintenue.

## Historiques cognitifs

`critic_history.jsonl` et `action_history.jsonl` sont limités à 10 Mio chacun.
Trois générations locales sont conservées (`.1` à `.3`). Les snapshots de la
boucle cognitive ne contiennent plus les objets complets de toutes les tâches.

Les historiques antérieurs au compactage sont archivés sous :

`/etc/neron/data/archive/cognitive/`

## Agents générés

Le registre dynamique canonique est :

`/etc/neron/data/generated_agents`

Les agents ne doivent plus être promus dans le submodule `core/`. Le workspace
reste la zone de génération et de test avant promotion.
