# Rapport Code Mort et Doublons

Date: 2026-06-02

## Regle appliquee

Aucune suppression n'a ete faite sans preuve d'inutilisation. Les elements ci-dessous sont classes comme "candidats" quand le scan ne prouve pas qu'ils sont morts.

## Imports casses corriges

- `core/status.py` importait `agents.watchdog_agent` et `modules.scheduler`, chemins legacy non valides dans le package actuel.
- Correction: imports remplaces par `core.agents.automation.watchdog_agent` et `core.modules.scheduler`.
- Test ajoute: `tests/test_status_module.py`.

## Script systemd obsolescent corrige

- `scripts/install_systemd.sh` referencait `deploy/neron.service`, absent du repertoire `deploy/`.
- Correction: installation des unites existantes et critiques.
- Test ajoute: `tests/test_systemd_services.py`.

## Doublons et candidats a consolidation

- Gateways Telegram:
  - `core/agents/communication/telegram_agent.py`
  - `core/gateway/telegram_gateway.py`
  - `core/agents/communication/telegram_patch.py`
  - Statut: a conserver pour l'instant. `telegram_agent.py` est le bot integre utilise par `core/app.py`; `telegram_gateway.py` appartient au control plane; `telegram_patch.py` ressemble a un patch historique documente mais aucune suppression n'est prouvee.
- WorldModel:
  - `core/world_model/*`
  - `core/memory/world_model/*`
  - Statut: deux surfaces differentes. La premiere gere l'etat systeme boucle/service, la seconde expose stockage/API enrichis. A documenter avant fusion.
- SelfModel agents:
  - `core/agents/self_model_agent.py`
  - `core/agents/core/self_model_agent.py`
  - Statut: doublon probable d'interface, mais pas supprime faute de preuve sur les chemins d'appel.
- Services deploy:
  - `deploy/*.service`
  - `deploy/systemd/*.service`
  - Statut: duplication partielle. Les unites actives correspondent aux fichiers `deploy/` pour les services critiques. `deploy/systemd/neron.service` pointe vers `server.core.app:app`, chemin legacy a ne pas utiliser sans migration.
- Backups de CodeAgent:
  - `core/agents/dev/data/code_backups/*.bak`
  - Statut: artefacts de sauvegarde. Candidat a deplacement hors package Python si leur retention n'est plus utile.

## Modules candidats a revue manuelle

- `core/agents/communication/telegram_patch.py`: fichier de patch/commentaires, pas un module runtime evident.
- `core/nano`: script sans extension Python sous `core`; verifier s'il est appele par des outils externes.
- `deploy/neron-cognitive-daemon.service` et `deploy/neron-vocal.service`: presents dans deploy mais absents de la liste des services critiques demandes.

## Imports inutilises

Pas de suppression automatique realisee. Le projet ne declare pas encore d'outil lint type Ruff/Flake8 dans la validation standard. Recommandation: ajouter une passe lint progressive en mode warning avant toute suppression.

## Dependances circulaires

Cycles statiques detectes autour des notifications Telegram:

- Telegram Agent <-> Evolution Supervisor
- Telegram Agent <-> Goal Orchestrator

Impact actuel limite, car les imports de notification sont differes dans les fonctions. Recommandation: extraire une interface `NotificationBus` ou reutiliser l'Event Bus pour decoupler les orchestrateurs de Telegram.

