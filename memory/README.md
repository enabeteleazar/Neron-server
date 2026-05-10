# Néron Obsidian Memory
## Description
Module de mémoire long terme pour Néron utilisant Obsidian comme base de connaissances locale.
Le système permet :
- l’enregistrement d’idées
- la recherche mémoire
- le stockage persistant lisible humainement
- l’intégration future avec agents autonomes et mémoire vectorielle
---
## Architecture
```text
Utilisateur
    ↓
NLP Router
    ↓
ObsidianAgent
    ↓
ObsidianMemory
    ↓
Vault Obsidian (.md)

⸻

## Emplacement du vault

/etc/neron/obsidian-vault

⸻

## Structure actuelle

obsidian-vault/
└── Ideas/

⸻

## Exemples API

Ajouter une idée

curl -X POST http://localhost:8010/input/text \
-H "x-api-key: API_KEY" \
-H "Content-Type: application/json" \
-d '{"text":"Ajoute une idée créer un agent autonome"}'

## Recherche mémoire

curl -X POST http://localhost:8010/input/text \
-H "x-api-key: API_KEY" \
-H "Content-Type: application/json" \
-d '{"text":"Cherche dans Obsidian agent autonome"}'

⸻

## Fichiers principaux

agents/memory/obsidian_agent.py
memory/obsidian/client.py
core/app.py

⸻

## Roadmap

* classification automatique
* tags intelligents
* mémoire vectorielle
* contexte injecté dans le LLM
* agent autonome auto-planificateur
* liaison Git automatique
* génération de tâches depuis les idées

⸻

## Version

V1 — mémoire Obsidian fonctionnelle

