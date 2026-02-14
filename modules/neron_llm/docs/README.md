# Néron LLM Service

Module d'abstraction du moteur LLM pour Néron AI Assistant.

## 📋 Description

Ce service agit comme un **wrapper HTTP** autour d'Ollama, fournissant une API standardisée pour interagir avec les modèles de langage.

### Responsabilités
- 🔌 Communication avec Ollama via HTTP
- 📝 Gestion des prompts et system prompts
- ⚙️ Configuration des paramètres de génération
- 🔍 Liste des modèles disponibles
- ✅ Health checks et monitoring

### Architecture

```
┌─────────────────┐      HTTP      ┌──────────────┐     HTTP API    ┌─────────────┐
│  Neron Core     │────────────────▶│  Neron LLM   │────────────────▶│   Ollama    │
│  (Orchestrator) │                 │  (Wrapper)   │                 │  (Engine)   │
└─────────────────┘                 └──────────────┘                 └─────────────┘
                                     Port: 5000                       Port: 11434
```

## 🚀 Démarrage rapide

### Prérequis
- Python 3.11+
- Ollama installé et en cours d'exécution
- Docker (optionnel)

### Installation locale

```bash
# Installer les dépendances
pip install -r requirements.txt

# Copier le fichier d'environnement
cp .env.example .env

# Modifier les variables selon votre configuration
nano .env

# Démarrer le service
python app.py
```

### Avec Docker

```bash
# Build l'image
docker build -t neron-llm .

# Lancer le conteneur
docker run -d \
  --name neron-llm \
  -p 5000:5000 \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  neron-llm
```

### Avec Docker Compose

Le service est déjà configuré dans le `docker-compose.yaml` principal :

```yaml
services:
  neron-llm:
    build: ./modules/neron_llm
    container_name: neron-llm
    ports:
      - "5000:5000"
    environment:
      - OLLAMA_HOST=http://neron-ollama:11434
      - LOG_LEVEL=INFO
    networks:
      - neron-network
```

## 📡 API Endpoints

### `GET /health`
Vérifie l'état du service et la connexion à Ollama.

**Réponse:**
```json
{
  "status": "healthy",
  "service": "Neron_LLM",
  "version": "1.0.0",
  "ollama_connected": true,
  "available_models": ["llama3.2:1b", "mistral"]
}
```

### `GET /models`
Liste tous les modèles disponibles.

**Réponse:**
```json
{
  "models": [
    {
      "name": "llama3.2:1b",
      "size": 1234567890,
      "digest": "abc123...",
      "modified_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### `POST /ask`
Génère une réponse à partir d'un prompt.

**Requête:**
```json
{
  "prompt": "Quelle est la capitale de la France ?",
  "model": "llama3.2:1b",
  "temperature": 0.7,
  "max_tokens": 2048,
  "system_prompt": "Tu es un assistant utile et concis.",
  "context": []
}
```

**Réponse:**
```json
{
  "response": "La capitale de la France est Paris.",
  "model": "llama3.2:1b",
  "tokens_used": 15,
  "generation_time": 1.23
}
```

### `POST /generate`
Alias pour `/ask` (compatibilité).

### `GET /`
Informations sur le service et les endpoints disponibles.

## ⚙️ Configuration

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|---------|
| `ENV` | Environnement (development/production) | `production` |
| `SERVICE_HOST` | Host du service | `0.0.0.0` |
| `SERVICE_PORT` | Port du service | `5000` |
| `OLLAMA_HOST` | URL d'Ollama | `http://localhost:11434` |
| `OLLAMA_TIMEOUT` | Timeout pour Ollama (secondes) | `300.0` |
| `DEFAULT_MODEL` | Modèle par défaut | `llama3.2:1b` |
| `MAX_TOKENS` | Nombre max de tokens | `2048` |
| `TEMPERATURE` | Température par défaut | `0.7` |
| `LOG_LEVEL` | Niveau de log | `INFO` |

## 🧪 Tests

```bash
# Installer les dépendances de test
pip install pytest pytest-asyncio httpx

# Lancer les tests
pytest tests/

# Avec coverage
pytest --cov=. tests/
```

### Test manuel avec curl

```bash
# Health check
curl http://localhost:5000/health

# Liste des modèles
curl http://localhost:5000/models

# Génération de texte
curl -X POST http://localhost:5000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Bonjour, comment vas-tu ?",
    "model": "llama3.2:1b"
  }'
```

## 🔧 Intégration avec Neron Core

Le service est utilisé par `neron-core` via le `OllamaClient`:

```python
from neron_core.llm.ollama_client import OllamaClient

# Configuration dans container.py
llm_client = OllamaClient(
    host="http://neron-llm:5000",
    model="llama3.2:1b"
)

# Utilisation
response = await llm_client.generate(
    prompt="Quelle est la météo aujourd'hui ?",
    system_prompt="Tu es un assistant météo."
)
```

## 📝 Structure des fichiers

```
modules/neron_llm/
├── app.py                 # Application FastAPI principale
├── config.py              # Configuration centralisée
├── models.py              # Modèles Pydantic
├── ollama_client.py       # Client HTTP pour Ollama
├── requirements.txt       # Dépendances Python
├── Dockerfile            # Image Docker
├── .env.example          # Exemple de configuration
├── README.md             # Cette documentation
└── tests/                # Tests unitaires
    ├── __init__.py
    ├── test_app.py
    └── test_ollama_client.py
```

## 🐛 Dépannage

### Le service ne démarre pas
- Vérifier que le port 5000 n'est pas déjà utilisé
- Vérifier les logs: `docker logs neron-llm`

### Impossible de se connecter à Ollama
- Vérifier qu'Ollama est en cours d'exécution
- Vérifier l'URL dans `OLLAMA_HOST`
- Tester: `curl http://localhost:11434/api/tags`

### Timeout lors de la génération
- Augmenter `OLLAMA_TIMEOUT`
- Vérifier les ressources système (CPU/RAM)
- Utiliser un modèle plus petit

## 📄 Licence

Ce module fait partie du projet Néron AI Assistant.

## 🤝 Contribution

Les contributions sont les bienvenues ! Merci de suivre les conventions de code du projet.
