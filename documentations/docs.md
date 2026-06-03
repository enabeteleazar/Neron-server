État interne

core/self_model

État du monde

core/world_model

Objectif actif

core/goal_system

Tâches actives

core/task_system

Noyau cognitif

core/cognitive_core

Score cognitif

core/cognitive/critic_engine.py

Critique interne

core/cognitive/critic_engine.py

Recommandations

core/cognitive/critic_engine.py

Historique d’auto-évaluation

/etc/neron/data/critic_history.jsonl

Mémoire long terme

core/memory + Obsidian

Événements cognitifs

core/events

Boucle cognitive

neron-cognitive-loop.service

Surveillance système

Watchdog + neron-doctor.service

Raisonnement LLM

core/llm_client + llm/

Routage d’intentions

core/pipeline/intent

Routage d’agents

core/pipeline/routing

Exécution agents

core/agents

Contrôle système

core/control_plane

Interface API

core/api + core/app.py

Persistance tâches

/etc/neron/data/tasks.json

Persistance objectifs

/etc/neron/data/goals.json

Persistance état monde

/etc/neron/data/world_model_state.json

Persistance cognitive

/etc/neron/data/critic_history.jsonl
