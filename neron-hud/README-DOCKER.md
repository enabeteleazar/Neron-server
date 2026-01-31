# JARVIS HUD - Docker Setup

Interface de type JARVIS pour assistant virtuel, utilisant Ollama comme LLM local.

## Prérequis

- Docker et Docker Compose installés
- Au moins 8GB de RAM (pour Ollama)

## Démarrage rapide

```bash
# 1. Lancer tous les services
docker-compose up -d

# 2. Télécharger un modèle Ollama (première fois seulement)
docker exec -it jarvis-ollama-1 ollama pull llama3.2

# 3. Accéder à l'application
# Ouvrir http://localhost:5000 dans votre navigateur
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| app | 5000 | Interface JARVIS |
| db | 5432 | PostgreSQL |
| ollama | 11434 | Serveur LLM |

## Configuration

### Utiliser un serveur Ollama existant

Si vous avez déjà Ollama installé sur votre machine, modifiez `docker-compose.yml` :

```yaml
services:
  app:
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Et supprimez le service `ollama` du fichier.

### Changer de modèle

Modifiez le modèle dans `server/routes.ts` :

```typescript
model: "llama3.2",  // Changez pour mistral, codellama, etc.
```

## Commandes utiles

```bash
# Voir les logs
docker-compose logs -f

# Arrêter les services
docker-compose down

# Reconstruire après modifications
docker-compose up -d --build

# Supprimer toutes les données
docker-compose down -v
```

## Modèles Ollama recommandés

- `llama3.2` - Bon équilibre performance/qualité
- `mistral` - Rapide et efficace
- `codellama` - Optimisé pour le code
- `llama3.2:70b` - Plus précis (nécessite plus de RAM)
