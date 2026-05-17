### SELF_model

## État actuel :

✅ état système temps réel
✅ CPU / RAM / disque
✅ uptime
✅ watchdog
✅ services actifs
✅ boucle cognitive
✅ historique intents
✅ mémoire cognitive
✅ activité récente
✅ événements EventBus
✅ persistance JSON
✅ monitoring loop
✅ connexion WorldModel
✅ connexion GoalSystem
✅ état mental / charge cognitive
✅ diagnostics & recommandations
✅ API self-model

## Architecture actuelle :

EventBus
   ↓
SelfModel Subscriber
   ↓
self_model_state.json
   ↓
SelfModel Loop
   ↓
/input/text → "etat interne"

## Le SelfModel sait désormais :

* observer son état interne
* observer ses événements cognitifs
* suivre ses objectifs actifs
* suivre son environnement
* maintenir une mémoire cognitive persistante

## Ce qu’il manque encore pour un “SelfModel avancé” :

⬜ auto-évaluation long terme
⬜ score de confiance cognitif
⬜ détection de dérive comportementale
⬜ historique de décisions pondéré
⬜ modèle de capacités agents
⬜ conscience des échecs répétés
⬜ prédiction de surcharge système
⬜ auto-adaptation comportementale
⬜ liens GoalSystem ↔ Planner ↔ Critic

