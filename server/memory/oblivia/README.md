# Oblivia — Memory Foundation

Oblivia est l’unique source de vérité mémoire de NéronOS.

## Flux

```text
Core → Provider Registry → A2A → Oblivia
Goal → Provider Registry → A2A → Oblivia
```

Le Core détecte et route les intentions. Il ne stocke, n’interprète et ne
reformule aucune connaissance. Les anciens imports
`core.modules.oblivia.*` sont uniquement des façades de compatibilité.

## Modèle

Oblivia conserve :

- les faits sémantiques sous forme `subject / predicate / object` ;
- les épisodes et traces runtime sous forme de `MemoryRecord` ;
- les documents durables dans Obsidian ;
- les index de recherche normalisés dans SQLite.

Le comportement des relations vient exclusivement de `ontology.py` :

- `immutable` conserve la première valeur et audite les conflits ;
- `replace` clôt la valeur courante et conserve son historique ;
- `accumulate` ajoute des valeurs sans doublon ;
- `preference` permet rétractation et réactivation du même tuple ;
- `event` est déclaré mais ne possède encore aucun prédicat.

Les faits partagent un cycle de vie générique (`valid_from`, `valid_to`,
`is_current`, rétractation et conflit). Aucun oubli ne supprime physiquement
une connaissance. La table historique `lives_at_facts` est conservée comme
source de migration compatible ; les nouvelles écritures vont dans
`knowledge_facts`.

Les décisions produit explicites sont :

- `name` est `replace`, avec historique visible ;
- `spouse` est `replace`, avec historique visible ;
- `likes` est `preference`, avec rétractation et réactivation.

## Reasoner déterministe

`reasoner.py` agrège exclusivement les faits structurés liés à `user`. Il
répond aux synthèses personnelles, alias familiaux, historiques d’emploi et
préférences actives/anciennes. Les faits rétractés ou conflictuels sont exclus
des réponses normales. Les `MemoryRecord` système/projet ne sont jamais
injectés dans une synthèse utilisateur.

Pour les historiques `lives_at` et `works_at`, la projection utilisateur est
d’abord triée par bornes temporelles, puis rendue unique par valeur normalisée
en conservant sa première apparition. Cette projection ne modifie jamais les
faits d’audit.

## Extensions prévues

- extracteur linguistique enrichi ;
- typage épisodique et procédural avancé ;
- graphe de connaissances ;
- embeddings et recherche vectorielle.
