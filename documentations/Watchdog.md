### WATCHDOG

## État actuel :

✅ surveillance réseau
✅ interfaces réseau
✅ gateway accessible
✅ DNS accessible
✅ services externes surveillés
✅ Home Assistant monitoring
✅ Ollama monitoring
✅ Néron Core API monitoring
✅ Néron LLM API monitoring
✅ état environnemental global
✅ diagnostics
✅ recommandations
✅ persistance JSON
✅ boucle world-model dédiée
✅ API /world-model/status
✅ API /world-model/summary
✅ intégré au SelfModel

## Architecture actuelle :

WorldModel Loop
    ↓
collecte environnement
    ↓
world_model_state.json
    ↓
API routes
    ↓
SelfModel

## Le WorldModel sait actuellement :

* observer l’état du réseau
* observer les services critiques
* détecter les indisponibilités
* produire un état environnemental global
* alimenter le SelfModel

## Ce qu’il manque encore pour un “WorldModel avancé” :

⬜ découverte automatique des services
⬜ topologie complète du réseau
⬜ état des machines distantes
⬜ latence historique
⬜ mémoire des incidents
⬜ analyse comportementale réseau
⬜ détection d’anomalies
⬜ prévision de panne
⬜ surveillance ressources GPU
⬜ état Docker/Kubernetes
⬜ compréhension contextuelle du monde externe
⬜ événements WorldModel → GoalSystem

