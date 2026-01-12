# Néron Core

Le module **Néron Core** constitue le codur de l'assistant Néron.
il gère la communication avec les autres modules via des messages standardisés('NeronMessage') et expose une API FastAPI pour interagir avec Néron.

---

## Fonctionnalité principales

- API FastAPI avec les endpoints:
    - '/'       : info sur le service.
    - '/health' : health check pour docker et monitoring.
    - '/status' : état des services internes et externes (Ollama, n8n, Node-RED).
    - '/chat'   : envoyer un message a Néron et recevoir la réponse.
- Integration du modèe 'NeronMessage" pour standardiser la communication interne.
- Orchestrator minimal pour traiter les messages entrants
- Scripts 'test.sh' pour tester rapidement Néron Core.

---

# Prérequis

- Python 3.11+ (ou version compatible)
- 'venv' pour gérer l'environnement virtuel
- Dépendances Pyhon:
    -''' bash
    pip install fastapi uvicorn httpx python-dotenv