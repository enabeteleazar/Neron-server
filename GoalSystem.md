### GOALSYSTEM

## État actuel :

✅ objectifs persistants
✅ objectifs système initiaux
✅ objectif actif
✅ priorités
✅ états (pending/active/completed/failed)
✅ persistance JSON
✅ API /goals
✅ API /goals/active
✅ création dynamique d’objectifs
✅ intégration SelfModel
✅ sélection automatique objectif actif

Architecture actuelle :

GoalSystem
    ↓
goals_state.json
    ↓
GoalManager
    ↓
SelfModel

## Le GoalSystem sait actuellement :

* stocker des objectifs
* sélectionner un objectif actif
* gérer des priorités
* exposer les objectifs via API
* alimenter le SelfModel

## Ce qu’il manque encore pour un “GoalSystem avancé” :

⬜ sous-objectifs hiérarchiques
⬜ dépendances réelles entre objectifs
⬜ scoring dynamique
⬜ expiration automatique
⬜ objectifs long terme
⬜ objectifs auto-générés
⬜ objectifs issus du WorldModel
⬜ objectifs issus du Critic
⬜ planification multi-objectifs
⬜ résolution de conflits d’objectifs
⬜ mémoire d’objectifs réussis/échoués
⬜ priorités adaptatives
⬜ objectifs contextuels
⬜ boucle motivationnelle

