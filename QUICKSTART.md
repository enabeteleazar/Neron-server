# 🚀 Quick Start Guide - Néron AI

Guide de démarrage rapide pour avoir Néron AI opérationnel en **moins de 10 minutes**.

-----

## ⚡ Installation Express (recommandée)

### One-liner

```bash
curl -fsSL https://raw.githubusercontent.com/enabeteleazar/Neron_AI/master/install.sh | bash
```

Le script vérifie et installe automatiquement :

- OS Ubuntu/Debian compatible
- RAM ≥ 2 GB, disque ≥ 10 GB
- Ollama (si absent)
- Clone du dépôt
- Environnement Python
- Création du `.env` depuis `.env.example`
- Téléchargement du modèle Ollama

**Puis démarrez :**

```bash
cd /etc/neron   # ou votre NERON_DIR personnalisé
make start
```

-----

## 🛠 Installation Manuelle (si besoin de personnaliser)

### Prérequis

```bash
# Vérifier Python
python3 --version
# Requis : Python 3.11+

# Vérifier l'espace disque
df -h
# Requis : Au moins 10 GB libres (modèles Ollama)

# Installer Ollama si absent
curl -fsSL https://ollama.com/install.sh | sh
```

### Installation en 4 Étapes

#### 1️⃣ Cloner le dépôt

```bash
git clone https://github.com/enabeteleazar/Neron_AI.git
cd Neron_AI
```

#### 2️⃣ Configurer

```bash
cp .env.example .env
nano .env
```

**Configuration minimale recommandée :**

```bash
# Modèle LLM (petit et rapide pour commencer)
OLLAMA_MODEL=llama3.2:1b

# STT
WHISPER_MODEL=base
WHISPER_LANGUAGE=fr

# Telegram (optionnel — laisser vide pour désactiver)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Watchdog (optionnel)
WATCHDOG_ENABLED=false

# Logs
LOG_LEVEL=INFO
```

#### 3️⃣ Installer les dépendances

```bash
make install
```

#### 4️⃣ Télécharger un modèle et démarrer

```bash
# Gérer le modèle interactivement
make ollama

# Lancer Néron
make start
```

-----

## 🤖 Configuration Telegram (optionnel)

```bash
# Assistant interactif : token + chat_id auto-détecté
make telegram
```

Néron démarre sans Telegram si les variables restent vides.

-----

## ✅ Vérification

### Statut des services

```bash
make status
# ou
curl http://localhost:8000/health
# {"status": "healthy", "version": "2.0.0"}
```

### Test de l’API

```bash
# Test texte
curl -X POST http://localhost:8000/input/text \
  -H "Content-Type: application/json" \
  -H "X-API-Key: votre_api_key" \
  -d '{"text": "Quelle heure est-il ?"}'
```

-----

## 🎯 Premiers Pas

### Exemple 1 : Chat Simple

```bash
curl -X POST http://localhost:8000/input/text \
  -H "Content-Type: application/json" \
  -H "X-API-Key: votre_api_key" \
  -d '{"text": "Explique-moi ce quest Ollama en une phrase"}'
```

### Exemple 2 : Consulter l’Historique

```bash
# 5 dernières conversations
curl http://localhost:8000/memory/retrieve?limit=5

# Rechercher dans l'historique
curl "http://localhost:8000/memory/search?query=docker&limit=10"
```

### Exemple 3 : Changer de Modèle LLM

```bash
# Assistant interactif
make ollama

# Ou manuellement
ollama pull llama3.2:3b
# Modifier OLLAMA_MODEL dans .env
make restart
```

### Exemple 4 : Transcription Audio (STT)

```bash
curl -X POST http://localhost:8000/input/audio \
  -H "X-API-Key: votre_api_key" \
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
curl -X POST http://localhost:8000/input/voice \
  -H "X-API-Key: votre_api_key" \
  -F "file=@mon_audio.wav" \
  -o reponse.wav

aplay reponse.wav

# Headers de réponse disponibles :
# X-Transcription    — texte reconnu
# X-Response-Text    — réponse de Néron
# X-Intent           — intent détecté
# X-STT-Latency-Ms   — latence STT
# X-TTS-Latency-Ms   — latence TTS
```

-----

## 🔧 Ajuster les Performances

**Système avec peu de RAM (< 4 GB) :**

```bash
# Dans .env
OLLAMA_MODEL=llama3.2:1b
WHISPER_MODEL=tiny
```

**Système standard (8-16 GB RAM) :**

```bash
# Dans .env
OLLAMA_MODEL=llama3.2:3b
WHISPER_MODEL=base
```

**Activer les logs détaillés :**

```bash
# Dans .env
LOG_LEVEL=DEBUG
make restart
```

-----

## 📊 Monitoring

### Health Check rapide

```bash
make status
```

### Métriques Prometheus

```bash
curl http://localhost:8000/metrics
```

### Logs en temps réel

```bash
make logs
# ou un service spécifique
journalctl -u neron -f
```

-----

## 🐛 Problèmes Courants

### Néron ne démarre pas

```bash
make logs
# Vérifier le .env
make env
```

### Port 8000 déjà utilisé

```bash
sudo lsof -i :8000
# Tuer le processus ou changer NERON_CORE_HTTP dans .env
```

### LLM trop lent

```bash
# Dans .env
OLLAMA_MODEL=llama3.2:1b
make restart
```

### STT transcription incorrecte

```bash
# Dans .env
WHISPER_LANGUAGE=fr
WHISPER_MODEL=small
make restart
```

### Ollama non accessible

```bash
systemctl status ollama
# Si arrêté :
ollama serve &
```

### Out of memory

```bash
# Modèle plus léger
ollama pull llama3.2:1b
# Dans .env : OLLAMA_MODEL=llama3.2:1b
make restart
```

-----

## 📝 Commandes Utiles

### Makefile

```bash
make start          # Démarrer Néron
make stop           # Arrêter
make restart        # Redémarrer
make status         # État des services
make logs           # Logs en temps réel
make update         # Mettre à jour (git pull + restart)
make backup         # Sauvegarder les données
make restore        # Restaurer une sauvegarde
make test           # Lancer les tests
make ollama         # Gérer le modèle LLM
make telegram       # Configurer les bots Telegram
make env            # Afficher la configuration active
make version        # Version installée
make clean          # Nettoyer les fichiers temporaires
```

### Gestion des modèles Ollama

```bash
ollama list                          # Lister les modèles installés
ollama pull llama3.2:3b              # Télécharger un modèle
ollama rm llama3.2:1b                # Supprimer un modèle
ollama run llama3.2:1b "Bonjour"     # Tester un modèle
```

### Sauvegarde et restauration

```bash
make backup                          # Créer une sauvegarde
make restore                         # Restaurer la dernière sauvegarde
```

-----

## 🚀 Exemples Avancés

**Python :**

```python
import requests

API_KEY = "votre_api_key"

def ask_neron(question: str) -> str:
    response = requests.post(
        "http://localhost:8000/input/text",
        headers={"X-API-Key": API_KEY},
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
            headers={"X-API-Key": API_KEY},
            files={"file": f},
            timeout=180
        )
    with open(output_path, "wb") as f:
        f.write(response.content)
    print(f"Transcription : {response.headers.get('X-Transcription')}")
    print(f"Réponse       : {response.headers.get('X-Response-Text')}")

voice_neron("question.wav", "reponse.wav")
```

**Bash :**

```bash
ask_neron() {
    curl -s -X POST http://localhost:8000/input/text \
        -H "Content-Type: application/json" \
        -H "X-API-Key: votre_api_key" \
        -d "{\"text\": \"$1\"}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['response'])"
}

ask_neron "Quelle est la capitale de la France ?"
```

-----

## ✅ Checklist de Démarrage

- [ ] Python 3.11+ disponible
- [ ] Ollama installé et fonctionnel (`ollama --version`)
- [ ] `.env` configuré (modèle, langue, API key)
- [ ] `make install` exécuté sans erreur
- [ ] Modèle Ollama téléchargé (`make ollama`)
- [ ] Néron démarré (`make start`)
- [ ] Health check réussi (`make status`)
- [ ] Test `/input/text` réussi
- [ ] Telegram configuré si souhaité (`make telegram`)

**Félicitations ! 🎉 Néron AI v2.0.0 est opérationnel !**

-----

**Temps total estimé : 5-10 minutes**

Pour aller plus loin, consultez la [documentation complète](README.md) et le [CHANGELOG](CHANGELOG.md).