# Audit des sources d'identité

## Source canonique

`NERON.md` définit désormais le nom, le rôle, la mission, la description et la
version de Néron. `core/identity/loader.py` relit ce document à chaque appel.

## Définitions runtime identifiées

| Fichier | Définition historique | Traitement |
| --- | --- | --- |
| `core/self_model/self_model.py` | nom, rôle, langue, version | remplacée par `get_identity()` |
| `core/app.py` | nom de service et version API | dérivés du loader |
| `core/personality/persona.yaml` | nom, rôle, version, prompt système | supprimée; comportement seulement |
| `core/personality/loader.py` | identité protégée issue du YAML | identité injectée depuis le loader |
| `neron.yaml` | version et prompt système | supprimés |
| `core/config.py` | version et prompt de repli | dérivés du loader |
| `core/modules/sessions.py` | prompts de session par défaut | dérivés du loader |
| `core/gateway/gateway.py` | prompt gateway par défaut | dérivé du loader |
| `core/modules/skills.py` | rôle dans la skill intégrée | dérivé du loader |
| `core/agents/communication/telegram_agent.py` | présentation Telegram | dérivée du loader |
| `core/gateway/telegram_gateway.py` | présentation Telegram | dérivée du loader |
| `deploy/neron-core.service` | description « autonomous assistant » | description technique générique |
| `deploy/systemd/neron.service` | description legacy « autonomous assistant » | description technique générique |
| `data/self_model.json` | ancien snapshot d'identité | cache uniquement, jamais lu comme source |
| `data/self_model_state.json` | ancien snapshot d'identité | cache uniquement, écrasé par `SelfModel` |

## Interfaces

Les interfaces suivies comme sous-modules Git (`ui_dashboard`, `ui_client`,
`ui_vocal`) contenaient des libellés d'identité statiques. Elles consomment
désormais `identity` depuis `/self-model/context`; leurs métadonnées génériques
ne définissent plus l'identité système.

## Documentation historique

Les fichiers sous `documentations/` décrivent des états d'architecture passés.
Ils ne sont pas chargés au runtime et ne constituent pas des sources d'identité.
