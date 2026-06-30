# Contrat Goal Engine → SelfModel

`SelfModelClient` est la façade interne en lecture utilisée par Goal Engine.
Elle ne crée pas un second SelfModel et ne passe pas par HTTP à l'intérieur du
Core.

Avant de construire un plan, Goal Engine consulte :

- l'état consolidé ;
- les capacités disponibles ;
- les providers ;
- les agents A2A ;
- le Memory Provider ;
- l'architecture.

La sélection suit cet ordre :

1. agent A2A compatible annoncé par SelfModel ;
2. provider compatible annoncé par SelfModel ;
3. fallback local explicite si le SelfModel est indisponible ou périmé ;
4. demande de création d'agent si aucune capacité ne correspond.

L'exécution continue de passer par `A2AClient` pour les agents et par
`ProviderRegistry` pour invoquer le provider nommé par le SelfModel.
