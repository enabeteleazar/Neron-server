# EvolutionSupervisor

## Rôle

`EvolutionSupervisor` est le module central d'évolution supervisée de Néron.
Il autorise l'auto-évaluation et la préparation de missions, mais interdit toute
exécution sans validation humaine explicite.

Principes fixes :

- `AUTO_EVOLUTION = true`
- `AUTO_APPROVAL = false`

Néron peut observer, analyser, proposer, préparer un prompt Codex et attendre une
validation. Il ne lance Codex, les tests, le commit et le push qu'après acceptation
utilisateur.

## Boucle

La boucle V1 est :

1. Observer l'état local de Néron.
2. Générer 3 propositions maximum.
3. Soumettre les propositions via Telegram, API et logs.
4. Attendre `/accept_evolution <n>` ou un appel API d'acceptation.
5. Créer un projet `type=evolution`.
6. Lancer Codex dans `/etc/neron`.
7. Lancer les tests obligatoires.
8. Commit/push seulement si les tests passent.
9. Générer de nouvelles propositions.
10. Attendre une nouvelle validation.

Une seule mission d'évolution peut être active à la fois.

## Commandes Telegram

- `propose les prochaines évolutions`
- `quelles sont les prochaines évolutions ?`
- `/evolution propose`
- `/evolution status`
- `/accept_evolution 1`
- `/reject_evolution 1`
- `/evolution_status`
- `/evolution_stop`

Les réponses restent courtes et ne contiennent pas les logs complets.

## Endpoints API

- `GET /evolution/status`
- `POST /evolution/propose`
- `GET /evolution/proposals`
- `POST /evolution/accept/{proposal_id}`
- `POST /evolution/reject/{proposal_id}`
- `POST /evolution/stop`
- `GET /evolution/runs`

`proposal_id` peut être un identifiant court (`evo_xxxxxx`) ou l'index affiché
dans le dernier cycle (`1`, `2`, `3`).

## Sécurité

- Aucune proposition n'est exécutée sans acceptation.
- Aucun second run ne démarre si un run est déjà `pending` ou `running`.
- Codex réel n'est appelé que par `CodexRunner` au runtime.
- `/evolution/status` expose `codex_available`, `codex_bin`,
  `codex_error`, `codex_version` et `codex_exec_supported_options`.
- Les tests unitaires injectent un runner factice.
- Les logs sont filtrés par `redact_secrets`.
- Aucun commit n'est tenté si Codex ou les tests échouent.
- Aucun push n'est tenté si le commit échoue.
- Obsidian n'est pas utilisé comme stockage opérationnel.

## Configuration systemd

Le service systemd peut avoir un `PATH` plus restreint que le shell utilisateur.
Il faut configurer explicitement le binaire Codex si nécessaire :

```ini
Environment="NERON_CODEX_BIN=/chemin/vers/codex"
```

Sans cette variable, `CodexRunner` cherche `codex` dans le `PATH`, puis dans
`/home/neron/.local/bin/codex`, `/usr/local/bin/codex` et `/usr/bin/codex`.
Si aucun binaire exécutable n'est trouvé, le run échoue avec :

```text
Codex CLI introuvable. Configure NERON_CODEX_BIN ou PATH systemd.
```

Avant toute exécution réelle, `CodexRunner` lance `codex exec --help`, détecte
les options disponibles, puis construit une commande ne contenant que les options
supportées par la version installée.

## Stockage

L'état opérationnel est stocké dans :

- `data/evolution_state.json`

Ce fichier contient les propositions, décisions utilisateur et runs récents.
Les exécutions validées créent aussi un projet via `ProjectManager` avec :

- `type = evolution`
- `status = pending | running | completed | failed | cancelled`
- `metadata.proposal_id`
- `metadata.codex_prompt`
- `metadata.tests`
- `metadata.commit_hash`
- `metadata.branch`

## Limites V1

- L'exécution API d'acceptation est synchrone. Elle est contrôlée et testable,
  mais peut bloquer la requête pendant Codex/tests.
- Le moteur de propositions utilise des règles locales simples : TODO/FIXME,
  projets failed, routes manquantes, documentation manquante, agents générés non
  routés.
- Le stop annule l'état et demande l'arrêt du subprocess courant si le runner en
  possède un, mais ne garantit pas l'annulation d'actions déjà terminées.
- Le LLM n'est pas obligatoire pour générer les propositions.

## Futures évolutions

- Worker asynchrone durable pour ne jamais bloquer l'API.
- Détails de runs consultables par endpoint dédié.
- Analyse plus riche des logs récents et des incohérences registry/projects.
- Confirmation dédiée pour les missions à risque élevé.
