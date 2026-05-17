# 🛡️ Néron Control Plane — Roadmap

## ✅ Fait

- Health checks des services (Core, STT, Memory, LLM, Web Voice)
- Notifications Telegram (DOWN / UP / Performance dégradée)
- Nom complet du service dans les alertes
- Historique SQLite
- Configuration JSON par service ()
- Intégration Docker avec réseau 

-----

## 🔧 En cours

- [ ] Fix SSL  (HTTPS avec certificat auto-signé)

-----

## 📋 Backlog

### Couche Résilience

- [ ] **Option 3 — Retry intelligent**
  - Si DOWN détecté → retry après 10s
  - Si toujours DOWN → alerte Telegram
  - Si revenu → log “micro-coupure détectée” sans alerte
  - Évite les faux positifs sur micro-coupures

### Couche Métriques Système

- [ ] **Collecteur ** via 
  - CPU : usage %, load average 1/5/15min
  - RAM : total, utilisée, libre, %
  - Disque : , , 
  - Réseau : bytes in/out (optionnel)
- [ ] **Seuils configurables dans **
  
  

### Couche Détection Intelligente

- [ ] **Seuils dynamiques** — baseline + déviation
- [ ] **Détection de patterns** — analyse comportementale
  - CPU > 85% ponctuellement → OK
  - CPU > 85% chaque nuit à 3h → Pattern détecté
  - CPU > 85% hors pattern → Anomalie
- [ ] **Comparaison historique** — comportement normal vs déviation
- [ ] **Réduction des faux positifs** — apprentissage adaptatif

### Couche Mémoire Stratégique

- [ ] **Fichiers JSONL dans **
  - 
  - 
  - 
  - 
- [ ] Chaque entrée traceable et corrélable
- [ ] Indépendante du code — survit aux mises à jour

### Couche Actions Correctives

- [ ] **Pipeline obligatoire** :
1. Détection
1. Analyse contextuelle
1. Décision
1. Action automatique
1. Alerte Telegram enrichie
1. Logging
1. Enregistrement mémoire stratégique
- [ ] **Actions disponibles** :
  - Restart service Docker
  - Nettoyage disque
  - Alerte escalade

### Couche Bot Telegram Bidirectionnel

- [ ] **Commandes disponibles** :
  -  — rapport complet de tous les services
  -  — état d’un service spécifique
  -  — CPU, RAM, disque
  -  — incidents des dernières 24h
  -  — redémarrer un service (avec confirmation)
- [ ] Authentification par 
- [ ] Listener polling ou webhook Telegram

### Couche Alertes Enrichies

- [ ] **Format Telegram complet** :
  - Timestamp
  - Niveau (INFO / WARNING / CRITICAL)
  - Description
  - Décision prise
  - Action réalisée
  - Impact potentiel

-----

## 🏗️ Architecture cible



-----

## 📁 Data Layout



-----

## 🔢 Priorités

|Priorité|Feature                     |Status    |
|--------|----------------------------|----------|
|1       |Fix SSL neron_web_voice     |🔧 En cours|
|2       |Retry intelligent (Option 3)|📋 Backlog |
|3       |Métriques système (psutil)  |📋 Backlog |
|4       |Mémoire stratégique JSONL   |📋 Backlog |
|5       |Bot Telegram bidirectionnel |📋 Backlog |
|6       |Détection de patterns       |📋 Backlog |
|7       |Actions correctives         |📋 Backlog |
