# Analyse du module neron_llm

## 🔴 Problèmes identifiés

### 1. **app.py** - Erreurs critiques
- ❌ Import `subprocess` manquant
- ❌ Utilisation de CLI `ollama` au lieu de l'API HTTP
- ❌ Incohérence du port (5000 dans Dockerfile, 11434 dans docker-compose)
- ❌ Variable `OLLAMA_HOST` qui pointe vers `neron-ollama` (service inexistant)

### 2. **ollama_client.py** - Fichier vide
- ❌ Seulement un placeholder, aucune implémentation

### 3. **Dockerfile** - Configuration incohérente
- ⚠️ Port 5000 dans CMD, mais 11434 attendu
- ⚠️ Ollama n'est pas installé dans l'image
- ⚠️ Approche incorrecte : le service devrait être un wrapper API, pas installer Ollama

### 4. **Architecture confuse**
- Le docker-compose.yaml principal utilise `neron-ollama` (port 5000)
- Le docker-compose de neron_core utilise `neron-llm` (port 11434)
- Deux services différents pour la même fonction ?

### 5. **Requirements manquants**
- Pas de `httpx` pour les appels HTTP asynchrones
- Pas de gestion d'erreurs appropriée

## 📋 Architecture recommandée

### Option 1 : Service wrapper autour d'Ollama (RECOMMANDÉ)
```
neron-llm (wrapper API) → communique avec → Ollama (service séparé)
     Port 5000                                  Port 11434
```

### Option 2 : Service tout-en-un
```
neron-llm (intègre Ollama directement)
     Port 11434
```

## ✅ Solution proposée

Je recommande **l'Option 1** car :
- Séparation des responsabilités
- Ollama peut être remplacé facilement
- Meilleure testabilité
- Conforme à l'architecture microservices

## 🔧 Fichiers à créer/corriger

1. ✅ **app.py** - Service FastAPI qui wrappé l'API Ollama
2. ✅ **config.py** - Configuration centralisée
3. ✅ **ollama_client.py** - Client HTTP pour communiquer avec Ollama
4. ✅ **models.py** - Modèles Pydantic
5. ✅ **Dockerfile** - Image Python simple sans Ollama
6. ✅ **requirements.txt** - Dépendances mises à jour
7. ✅ **docker-compose.yaml** - Définir les deux services

## 🎯 Harmonisation avec neron-core

Le `neron-core` utilise `OllamaClient` qui doit communiquer avec ce service.
Il faudra s'assurer que :
- Les URLs sont cohérentes
- Les modèles de données sont compatibles
- Les timeouts sont bien configurés
