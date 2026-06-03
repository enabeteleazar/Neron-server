# Decision Surface Telegram

Date: 2026-06-02

## Surface principale

La surface Telegram principale du service `neron-core` est:

- `core.agents.communication.telegram_agent`
- demarrage depuis `core.app` via `start_bot()`

Cette surface enregistre les commandes Telegram actuelles et passe les commandes d'orchestration par `NeronCommandDispatcher`.

## Surface de compatibilite

`core.gateway.telegram_gateway.TelegramGateway` est conserve pour le control-plane stack:

- reference par `core.control_plane.core.NeronCore`
- utilise `InternalGateway`
- ne doit pas etre lance concurremment avec le bot principal sur le meme token Telegram

## Legacy

`core.agents.communication.telegram_patch.py` est marque comme notes de patch legacy. Il ne doit pas etre utilise comme surface runtime.

## Decision

- Actif runtime: `core.agents.communication.telegram_agent`
- Compatibilite control-plane: `core.gateway.telegram_gateway`
- Legacy documentaire: `core.agents.communication.telegram_patch`

## Risque restant

Deux bots Telegram utilisant le meme token peuvent entrer en conflit si le control-plane et `neron-core` demarrent simultanement leurs surfaces Telegram. La configuration systemd officielle doit privilegier `neron-core`.

