# 🚀 Quick Start Guide - Néron AI

Guide de démarrage rapide pour avoir Néron AI opérationnel en **moins de 10 minutes**.

## ⚡ Installation Express (5 minutes)

### Prérequis

Avant de commencer, vérifiez que vous avez :

```bash
# Vérifier Docker
docker --version
# Requis: Docker version 20.10+

# Vérifier Docker Compose
docker compose version
# Requis: Docker Compose version 2.0+

# Vérifier l'espace disque
df -h
# Requis: Au moins 20 GB libres
```

Si Docker n’est pas installé :

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Redémarrer ou se relogger
```

### Installation en 4 Étapes

#### 1️⃣ Télécharger Néron AI

```bash
# Cloner le dépôt
git clone https://github.com/yourusername/neron-ai.git
cd neron-ai

# OU télécharger la release
wget https://github.com/yourusername/neron-ai/archive/refs/tags/v1.0.0.tar.gz
tar -xzf v1.0.0.tar.gz
cd neron-ai-1.0.0
```

#### 2️⃣ Créer le Réseau Docker

```bash
docker network create Neron_Network
```

#### 3️⃣ Configurer

```bash
# Créer le fichier de configuration
mkdir -p /opt/Homebox_AI
cp .env.example /opt/Homebox_AI/.env

# Configuration minimale (optionnel - les valeurs par défaut fonctionnent)
nano /opt/Homebox_AI/.env
```

**Configuration minimale recommandée :**

```bash
# Ports (laisser par défaut)
NERON_CORE_HTTP=8000
NERON_LLM_HTTP=11434

# Modèle LLM (petit et rapide)
OLLAMA_MODEL=llama3.2:1b

# Modèle STT (rapide)
WHISPER_MODEL=base

# Logs
LOG_LEVEL=INFO
```

#### 4️⃣ Lancer !

```bash
# Tout en une commande
./start_neron.sh

# OU manuellement
docker compose up -d

# Attendre que les services démarrent (30-60 secondes)
docker compose logs -f
# Appuyer sur Ctrl+C quand vous voyez "Application startup complete"
```

### 📦 Télécharger un Modèle LLM

```bash
# Modèle recommandé pour débuter (1 GB)
docker exec -it neron_ollama ollama pull llama3.2:1b

# OU un modèle plus précis mais plus lourd (4 GB)
docker exec -it neron_ollama ollama pull mistral
```

**Temps de téléchargement :** 5-10 minutes selon votre connexion.

## ✅ Vérification

### Test Rapide

```bash
# 1. Vérifier que tous les services sont démarrés
docker compose ps

# Vous devriez voir :
# neron_core      - Up (healthy)
# neron_llm       - Up (healthy)
# neron_ollama    - Up (healthy)
# neron_stt       - Up (healthy)
# neron_memory    - Up (healthy)
# neron_web       - Up
```

### Test de l’API

```bash
# Test du service Core
curl http://localhost:8000/health

# Réponse attendue :
# {"status": "healthy"}

# Test de génération
curl -X POST http://localhost:8000/input/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Dis bonjour en français"}'

# Réponse attendue :
# {
#   "response": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
#   "metadata": {"model": "llama3.2:1b"}
# }
```

### Test de l’Interface Web

```bash
# Ouvrir dans votre navigateur
http://localhost:7860
```

Vous devriez voir l’interface de chat Néron AI. Tapez un message et cliquez sur “Submit” !

## 🎯 Premiers Pas

### Exemple 1 : Chat Simple

**Via l’interface web :**

1. Ouvrir http://localhost:7860
1. Taper : “Explique-moi ce qu’est Docker en une phrase”
1. Cliquer “Submit”

**Via l’API :**

```bash
curl -X POST http://localhost:8000/input/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Explique-moi ce qu est Docker en une phrase"}'
```

### Exemple 2 : Consulter l’Historique

```bash
# Récupérer les 5 dernières conversations
curl http://localhost:8002/retrieve?limit=5

# Rechercher dans l'historique
curl "http://localhost:8002/search?query=docker&limit=10"
```

### Exemple 3 : Changer de Modèle LLM

```bash
# Lister les modèles disponibles
docker exec -it neron_ollama ollama list

# Télécharger un nouveau modèle
docker exec -it neron_ollama ollama pull mistral

# Modifier la configuration
nano /opt/Homebox_AI/.env
# Changer: OLLAMA_MODEL=mistral

# Redémarrer
docker compose restart neron_core neron_llm
```

### Exemple 4 : Transcription Audio

```bash
# Enregistrer un fichier audio (ou utiliser un existant)
# Puis l'envoyer au service STT

curl -X POST http://localhost:8001/speech \
  -F "file=@mon_audio.wav"

# Réponse :
# {"text": "Transcription de votre audio"}
```

## 🔧 Configuration Rapide

### Ajuster les Performances

**Pour un système avec peu de RAM (< 8 GB) :**

```bash
# Dans .env
OLLAMA_MODEL=llama3.2:1b    # Modèle le plus léger
WHISPER_MODEL=tiny          # Modèle STT minimal
```

**Pour un système puissant (16 GB+ RAM) :**

```bash
# Dans .env
OLLAMA_MODEL=mistral        # Modèle plus précis
WHISPER_MODEL=medium        # Meilleure transcription
```

### Activer les Logs Détaillés

```bash
# Dans .env
LOG_LEVEL=DEBUG

# Redémarrer
docker compose restart
```

## 📊 Tableaux de Bord

### Health Check Dashboard

```bash
# Script de vérification rapide
cat > health_check.sh << 'EOF'
#!/bin/bash
echo "=== Néron AI Health Check ==="
echo ""
echo "Core:    $(curl -s http://localhost:8000/health | jq -r .status)"
echo "LLM:     $(curl -s http://localhost:5000/health | jq -r .status)"
echo "STT:     $(curl -s http://localhost:8001/health | jq -r .status)"
echo "Memory:  $(curl -s http://localhost:8002/health | jq -r .status)"
echo ""
echo "Conversations: $(curl -s http://localhost:8002/stats | jq -r .total_entries)"
EOF

chmod +x health_check.sh
./health_check.sh
```

### Monitoring en Temps Réel

```bash
# Suivre les logs de tous les services
docker compose logs -f

# Suivre les logs d'un service spécifique
docker compose logs -f neron_core

# Statistiques Docker
docker stats
```

## 🐛 Problèmes Courants

### Problème : Les services ne démarrent pas

**Solution :**

```bash
# Vérifier les logs d'erreur
docker compose logs

# Reconstruire les images
docker compose build --no-cache

# Relancer
docker compose up -d
```

### Problème : Port déjà utilisé

**Solution :**

```bash
# Identifier le processus qui utilise le port
sudo lsof -i :8000

# Option 1 : Tuer le processus
sudo kill -9 [PID]

# Option 2 : Changer le port dans .env
NERON_CORE_HTTP=8080
```

### Problème : Modèle LLM ne se télécharge pas

**Solution :**

```bash
# Vérifier la connexion réseau
curl -I https://ollama.ai

# Télécharger manuellement
docker exec -it neron_ollama bash
ollama pull llama3.2:1b
exit
```

### Problème : Réponses LLM très lentes

**Solutions :**

1. Utiliser un modèle plus petit : `llama3.2:1b`
1. Augmenter la RAM Docker (Settings > Resources)
1. Vérifier l’utilisation CPU : `docker stats`

### Problème : “Out of memory”

**Solution :**

```bash
# Augmenter la RAM Docker
# Docker Desktop > Settings > Resources > Memory > 8 GB minimum

# OU utiliser un modèle plus léger
docker exec -it neron_ollama ollama pull llama3.2:1b
```

## 📝 Commandes Utiles

### Gestion des Services

```bash
# Démarrer
docker compose up -d

# Arrêter
docker compose down

# Redémarrer un service
docker compose restart neron_core

# Voir les logs
docker compose logs -f neron_core

# Reconstruire
docker compose build --no-cache neron_llm
```

### Gestion des Modèles

```bash
# Lister les modèles installés
docker exec -it neron_ollama ollama list

# Télécharger un modèle
docker exec -it neron_ollama ollama pull [nom_modele]

# Supprimer un modèle
docker exec -it neron_ollama ollama rm [nom_modele]

# Tester un modèle
docker exec -it neron_ollama ollama run llama3.2:1b "Hello"
```

### Gestion de la Mémoire

```bash
# Statistiques
curl http://localhost:8002/stats

# Rechercher
curl "http://localhost:8002/search?query=test"

# Effacer toute la mémoire (⚠️ ATTENTION)
curl -X DELETE http://localhost:8002/clear

# Sauvegarder la base de données
docker cp neron_memory:/data/memory.db ./backup_$(date +%Y%m%d).db
```

### Nettoyage

```bash
# Arrêter et supprimer les conteneurs
docker compose down

# Supprimer aussi les volumes (⚠️ perte de données)
docker compose down -v

# Nettoyer les images non utilisées
docker image prune -a

# Nettoyer tout Docker
docker system prune -a --volumes
```

## 🚀 Étapes Suivantes

Maintenant que Néron AI fonctionne :

1. **Explorez l’API** : [API Documentation](docs/API.md)
1. **Personnalisez** : [Guide de Configuration](docs/CONFIGURATION.md)
1. **Développez** : [Guide de Contribution](CONTRIBUTING.md)
1. **Intégrez** : Utilisez l’API dans vos propres applications

### Exemples Avancés

**Python :**

```python
import requests

def ask_neron(question: str) -> str:
    response = requests.post(
        "http://localhost:8000/input/text",
        json={"text": question},
        timeout=60
    )
    return response.json()["response"]

# Utilisation
answer = ask_neron("Quelle est la capitale de la France ?")
print(answer)
```

**JavaScript :**

```javascript
async function askNeron(question) {
    const response = await fetch('http://localhost:8000/input/text', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: question})
    });
    const data = await response.json();
    return data.response;
}

// Utilisation
askNeron("Quelle est la capitale de la France ?")
    .then(answer => console.log(answer));
```

**cURL :**

```bash
#!/bin/bash
ask_neron() {
    curl -s -X POST http://localhost:8000/input/text \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$1\"}" \
        | jq -r '.response'
}

# Utilisation
ask_neron "Quelle est la capitale de la France ?"
```

## 📞 Besoin d’Aide ?

- 📖 **Documentation complète** : <README.md>
- 🐛 **Problèmes** : [GitHub Issues](https://github.com/yourusername/neron-ai/issues)
- 💬 **Questions** : [GitHub Discussions](https://github.com/yourusername/neron-ai/discussions)
- 📧 **Email** : support@neron-ai.example.com

## ✅ Checklist de Démarrage

- [ ] Docker et Docker Compose installés
- [ ] Réseau Docker créé
- [ ] Configuration `.env` copiée
- [ ] Services démarrés avec `./start_neron.sh`
- [ ] Modèle LLM téléchargé
- [ ] Health checks réussis
- [ ] Test API réussi
- [ ] Interface web accessible
- [ ] Premier chat réalisé

**Félicitations ! 🎉 Néron AI est opérationnel !**

-----

**Temps total estimé : 10-15 minutes**

Pour aller plus loin, consultez la [documentation complète](README.md).
