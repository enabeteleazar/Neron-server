# Tool Creator V1

## Rôle

`core/tools` transforme une demande de capacité absente en un petit ensemble de
tools déclaratifs, validés, enregistrés et exécutables par un runtime borné.
La V1 couvre le cas d'analyse des logs Néron sans lancer de commande système.

## Tool Creator et Agent Creator

Le Tool Creator prépare des opérations déterministes et sans état. L'Agent
Creator construit une capacité durable qui peut orchestrer des tools, conserver
un état ou fonctionner périodiquement. Une demande durable peut donc créer ses
tools avant la création de l'agent.

## Cycle `create_tool`

1. `CapabilityResolver` classe la demande.
2. `ToolCreator.plan_tools_for_request` produit des `ToolSpec`.
3. Chaque spec est validée; les commandes système sont interdites.
4. `ToolRegistry` ignore les tools déjà présents et persiste les nouveaux.
5. `ToolRuntime.execute_tool` appelle uniquement un handler Python connu ou
   injecté.
6. Les metadata du goal et du projet exposent `required_tools`,
   `created_tools` et `tool_creation_status`.

Pour les logs, le plan contient:

- `neron_log_reader_tool`;
- `neron_log_error_filter_tool`;
- `neron_log_summary_tool`.

Le lecteur consomme `payload.logs` ou un provider injecté. Les tests ne lisent
jamais le journal systemd réel.

## Intégration Capability Resolver

Avant de mettre en file un goal `create_tool` ou `create_agent`, le resolver
appelle `ensure_tools_for_request`. Pour une analyse durable des logs, les trois
tools sont donc enregistrés avant l'appel asynchrone à l'Agent Creator. Une
seconde demande réutilise les mêmes slugs.

Les endpoints authentifiés sont:

- `GET /tools`;
- `GET /tools/{slug}`;
- `POST /tools/{slug}/execute`.

Le endpoint d'exécution refuse les specs autorisant des commandes système.

## Limites V1

- Le planner reconnaît uniquement la famille d'analyse des logs.
- Le registre persiste des specs, pas du code arbitraire.
- Aucun accès direct à `journalctl`, au shell, au réseau ou au filesystem.
- La collecte réelle devra être fournie par un provider sûr et explicitement
  autorisé.
- Le runtime n'orchestre pas encore un graphe générique de tools.

## Suite

La prochaine étape est un Tool Runtime avancé avec providers approuvés,
contrats d'entrée validés, orchestration de pipelines, métriques, timeouts et
politiques de permissions par tool.
