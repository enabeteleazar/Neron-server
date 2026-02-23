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
git clone https://github.com/enabeteleazar/Neron_AI
cd Neron_AI

# OU télécharger la release
wget https://github.com/enabeteleazar/Neron_AI/archive/refs/tags/v1.6.0.tar.gz
tar -xzf v1.6.0.tar.gz
cd Neron_AI-1.6.0
```

#### 2️⃣ Créer le Réseau Docker

```bash
docker network create Neron_Network
```

#### 3️⃣ Configurer

```bash
# Créer le fichier de configuration
mkdir -p /opt/Neron_AI
cp .env.example /opt/Neron_AI/.env

# Configuration minimale (optionnel - les valeurs par défaut fonctionnent)
nano /opt/Neron_AI/.env
```

**Configuration minimale recommandée :**

```bash
# Ports (laisser par défaut)
NERON_CORE_HTTP=8000
NERON_LLM_HTTP=11434

# Modèle LLM (petit et rapide)
OLLAMA_MODEL=llama3.2:1b

# STT
WHISPER_MODEL=base
WHISPER_LANGUAGE=fr

# TTS
TTS_ENGINE=pyttsx3
TTS_LANGUAGE=fr

# Logs
LOG_LEVEL=INFO
```

#### 4️⃣ Lancer !

```bash
# Tout en une commande
docker compose --env-file /opt/Neron_AI/.env up -d

# Attendre que les services démarrent (30-60 secondes)
docker compose logs -f
# Appuyer sur Ctrl+C quand vous voyez "Application startup complete"
```

### 📦 Télécharger un Modèle LLM

```bash
# Modèle recommandé pour débuter (1 GB)
docker exec neron_ollama ollama pull llama3.2:1b

# OU modèle plus précis (4 GB, meilleur français)
docker exec neron_ollama ollama pull llama3.2:3b
```

**Temps de téléchargement :** 5-10 minutes selon votre connexion.

-----

## ✅ Vérification

### Test Rapide

```bash
# Vérifier que tous les services sont démarrés
docker compose ps

# Vous devriez voir :
# neron_core      - Up (healthy)
# neron_llm       - Up (healthy)
# neron_ollama    - Up (healthy)
# neron_stt       - Up (healthy)
# neron_memory    - Up (healthy)
# neron_tts       - Up (healthy)
# neron_searxng   - Up (healthy)
# neron_web       - Up
```

### Test de l’API

```bash
# Health check
curl http://localhost:8000/health
# {"status": "healthy", "version": "1.6.0"}

# Test texte
curl -X POST http://localhost:8000/input/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Quelle heure est-il ?"}'
```

### Test de l’Interface Web

Ouvrir **http://localhost:7860** dans votre navigateur. Tapez un message et cliquez sur “Submit” !

-----

## 🎯 Premiers Pas

### Exemple 1 : Chat Simple

```bash
curl -X POST http://localhost:8000/input/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Explique-moi ce quest Docker en une phrase"}'
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
docker exec neron_ollama ollama list

# Télécharger un nouveau modèle
docker exec neron_ollama ollama pull llama3.2:3b

# Modifier la configuration
nano /opt/Neron_AI/.env
# Changer: OLLAMA_MODEL=llama3.2:3b

# Redémarrer
docker compose restart neron_core
```

### Exemple 4 : Transcription Audio (STT)

```bash
# Envoyer un fichier audio → obtenir le texte transcrit
curl -X POST http://localhost:8000/input/audio \
  -F "file=@mon_audio.wav"

# Réponse :
# {
#   "response": "Réponse de Néron...",
#   "transcription": "Texte transcrit depuis l'audio",
#   "intent": "conversation"
# }
```

### Exemple 5 : Pipeline Vocal Complet (STT → LLM → TTS)

```bash
# Envoyer audio → obtenir audio en réponse
curl -X POST http://localhost:8000/input/voice \
  -F "file=@mon_audio.wav" \
  -o reponse.wav

# Lire la réponse audio
aplay reponse.wav

# Les headers de réponse contiennent les métadonnées :
# X-Transcription: texte reconnu
# X-Response-Text: réponse de Néron
# X-Intent: intent détecté
# X-STT-Latency-Ms: latence STT
# X-TTS-Latency-Ms: latence TTS
```

-----

## 🔧 Configuration Rapide

### Ajuster les Performances

**Pour un système avec peu de RAM (< 8 GB) :**

```bash
# Dans .env
OLLAMA_MODEL=llama3.2:1b    # Modèle le plus léger (~38s)
WHISPER_MODEL=tiny          # STT minimal (~3s)
```

**Pour un système standard (8-16 GB RAM) :**

```bash
# Dans .env
OLLAMA_MODEL=llama3.2:3b    # Meilleur français (~86s CPU)
WHISPER_MODEL=base          # Bon compromis (~8s)
```

### Activer les Logs Détaillés

```bash
# Dans .env
LOG_LEVEL=DEBUG

# Redémarrer
docker compose restart
```

-----

## 📊 Monitoring

### Health Check Dashboard

```bash
cat > health_check.sh << 'EOF'
#!/bin/bash
echo "=== Néron AI Health Check ==="
echo ""
echo "Core:     $(curl -s http://localhost:8000/health | jq -r .status)"
echo "LLM:      $(curl -s http://localhost:5000/health | jq -r .status)"
echo "STT:      $(curl -s http://localhost:8001/health | jq -r .status)"
echo "TTS:      $(curl -s http://localhost:8003/health | jq -r .status)"
echo "Memory:   $(curl -s http://localhost:8002/health | jq -r .status)"
echo ""
echo "Conversations: $(curl -s http://localhost:8002/stats | jq -r .total_entries)"
echo ""
echo "Métriques: curl http://localhost:8000/metrics"
EOF

chmod +x health_check.sh
./health_check.sh
```

### Métriques Prometheus

```bash
curl http://localhost:8000/metrics
```

### Monitoring en Temps Réel

```bash
# Logs de tous les services
docker compose logs -f

# Un service spécifique
docker compose logs -f neron_core

# Statistiques ressources
docker stats
```

-----

## 🐛 Problèmes Courants

### Services ne démarrent pas

```bash
docker compose logs
docker compose build --no-cache
docker compose up -d
```

### Port déjà utilisé

```bash
sudo lsof -i :8000
# Option 1 : tuer le processus
sudo kill -9 [PID]
# Option 2 : changer le port dans .env
NERON_CORE_HTTP=8080
```

### LLM trop lent

```bash
# Utiliser un modèle plus léger
OLLAMA_MODEL=llama3.2:1b
```

### STT transcription incorrecte

```bash
# Vérifier la langue dans .env
WHISPER_LANGUAGE=fr

# Ou utiliser un modèle plus précis
WHISPER_MODEL=small
```

### Réseau introuvable

```bash
docker network create Neron_Network
docker compose up -d
```

### Out of memory

```bash
# Modèle plus léger
docker exec neron_ollama ollama pull llama3.2:1b
# Dans .env : OLLAMA_MODEL=llama3.2:1b
```

-----

## 📝 Commandes Utiles

### Gestion des Services

```bash
docker compose up -d                          # Démarrer
docker compose down                           # Arrêter
docker compose restart neron_core             # Redémarrer un service
docker compose logs -f neron_core             # Logs
docker compose build --no-cache neron_stt     # Reconstruire
```

### Gestion des Modèles LLM

```bash
docker exec neron_ollama ollama list                    # Lister
docker exec neron_ollama ollama pull llama3.2:3b        # Télécharger
docker exec neron_ollama ollama rm llama3.2:1b          # Supprimer
docker exec neron_ollama ollama run llama3.2:1b "Hello" # Tester
```

### Gestion de la Mémoire

```bash
curl http://localhost:8002/stats                    # Statistiques
curl "http://localhost:8002/search?query=test"      # Rechercher
curl -X DELETE http://localhost:8002/clear          # ⚠️ Tout effacer
docker cp neron_memory:/data/memory.db ./backup_$(date +%Y%m%d).db  # Sauvegarder
```

### Nettoyage

```bash
docker compose down            # Arrêter
docker compose down -v         # ⚠️ Arrêter + supprimer volumes
docker image prune -a          # Nettoyer images
docker system prune -a --volumes  # Nettoyer tout
```

-----

## 🚀 Étapes Suivantes

### Exemples Avancés

**Python :**

```python
import requests

def ask_neron(question: str) -> str:
    response = requests.post(
        "http://localhost:8000/input/text",
        json={"text": question},
        timeout=120
    )
    return response.json()["response"]

print(ask_neron("Quelle est la capitale de la France ?"))
```

**Pipeline vocal Python :**

```python
import requests

def voice_neron(audio_path: str, output_path: str):
    with open(audio_path, "rb") as f:
        response = requests.post(
            "http://localhost:8000/input/voice",
            files={"file": f},
            timeout=180
        )
    with open(output_path, "wb") as f:
        f.write(response.content)
    print(f"Transcription : {response.headers.get('X-Transcription')}")
    print(f"Réponse       : {response.headers.get('X-Response-Text')}")

voice_neron("question.wav", "reponse.wav")
```

**cURL :**

```bash
ask_neron() {
    curl -s -X POST http://localhost:8000/input/text \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$1\"}" \
        | jq -r '.response'
}

ask_neron "Quelle est la capitale de la France ?"
```

-----

## ✅ Checklist de Démarrage

- [ ] Docker et Docker Compose installés
- [ ] Réseau Docker créé (`docker network create Neron_Network`)
- [ ] Configuration `.env` copiée et adaptée
- [ ] Services démarrés (`docker compose up -d`)
- [ ] Modèle LLM téléchargé
- [ ] Health checks réussis (`./health_check.sh`)
- [ ] Test `/input/text` réussi
- [ ] Interface web accessible (http://localhost:7860)
- [ ] Pipeline vocal `/input/voice` testé

**Félicitations ! 🎉 Néron AI v1.6.0 est opérationnel !**

-----

**Temps total estimé : 10-15 minutes**

Pour aller plus loin, consultez la [documentation complète](README.md) et le [CHANGELOG](CHANGELOG.md).
