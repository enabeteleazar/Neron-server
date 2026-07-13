# French Text Normalizer

Le French Text Normalizer est une brique commune du Core NeronOS. Son role est
de transformer les formulations utilisateur en une forme stable avant le
routage d'intentions, sans modifier le texte brut utilise pour executer les
actions, repondre a l'utilisateur ou memoriser une information.

## Emplacement

Module principal:

`server/core/pipeline/nlp/french_normalizer.py`

Integration:

1. API, Telegram, Voice Interface, Mobile ou transcription STT recoivent un
   texte brut.
2. `CoreOrchestrator.decide()` calcule `normalized_query`.
3. `IntentRouter` et les detecteurs locaux utilisent la version normalisee.
4. `CoreOrchestrator._execute()` recoit encore la requete originale.

Les detecteurs identity, timer, status et memory deleguent aussi leur
normalisation a ce composant. Le resolver de capacites reutilise la meme source
via `modules.capabilities.router.normalize_text`.

## Fonctionnement

Le normalizer applique des transformations linguistiques legeres:

- normalisation Unicode;
- minuscules;
- suppression des accents pour le matching;
- espaces multiples compactes;
- ponctuation non utile retiree;
- apostrophes et tirets convertis en formes comparables;
- corrections grammaticales simples, par exemple `qui est tu` -> `qui es tu`;
- variantes orales/STT, par exemple suppression de `euh`, `heu`;
- synonymie de commande tres limitee, par exemple `demarre` -> `lance`.

Cette couche n'est pas un dictionnaire de phrases. Les nouvelles regles doivent
rester generiques et manipuler des tokens.

## Ajouter une regle

1. Ajouter une fonction `list[str] -> list[str]` dans
   `french_normalizer.py`.
2. L'ajouter dans `FrenchTextNormalizer.rules`.
3. Ajouter au moins un test dans `tests/test_french_text_normalizer.py`.
4. Verifier que le texte brut reste disponible dans les executants.

## Evolution

L'API publique `normalize_text(text: str) -> str` permet de remplacer ou
completer les regles par un modele NLP/LLM local de reecriture canonique, sans
changer les points d'entree du Core.
