# 🛡️ Néron Control Plane — Roadmap

## ✅ Fait

- Health checks des services (Core, STT, Memory, LLM, Web Voice)
- Notifications Telegram (DOWN / UP / Performance dégradée)
- Nom complet du service dans les alertes
- Historique SQLite
- Configuration JSON par service (`neron.json`)
- Intégration Docker avec réseau `neron_internal`

-----

## 🔧 En cours

- [ ] Fix SSL `neron_web_voice` (HTTPS avec certificat auto-signé)

-----

## 📋 Backlog

### Couche Résilience

- [ ] **Option 3 — Retry intelligent**
  - Si DOWN détecté → retry après 10s
  - Si toujours DOWN → alerte Telegram
  - Si revenu → log “micro-coupure détectée” sans alerte
  - Évite les faux positifs sur micro-coupures

### Couche Métriques Système

- [ ] **Collecteur `src/collectors/system.py`** via `psutil`
  - CPU : usage %, load average 1/5/15min
  - RAM : total, utilisée, libre, %
  - Disque : `/`, `/mnt/Data`, `/mnt/usb-storage`
  - Réseau : bytes in/out (optionnel)
- [ ] **Seuils configurables dans `config.yaml`**
  
  ```yaml
  thresholds:
    cpu_warn: 75
    cpu_critical: 90
    ram_warn: 80
    ram_critical: 95
    disk_warn: 75
    disk_critical: 90
  ```

### Couche Détection Intelligente

- [ ] **Seuils dynamiques** — baseline + déviation
- [ ] **Détection de patterns** — analyse comportementale
  - CPU > 85% ponctuellement → OK
  - CPU > 85% chaque nuit à 3h → Pattern détecté
  - CPU > 85% hors pattern → Anomalie
- [ ] **Comparaison historique** — comportement normal vs déviation
- [ ] **Réduction des faux positifs** — apprentissage adaptatif

### Couche Mémoire Stratégique

- [ ] **Fichiers JSONL dans `/mnt/Data/memory/`**
  - `events.jsonl`
  - `anomalies.jsonl`
  - `decisions.jsonl`
  - `actions.jsonl`
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
  - `/status` — rapport complet de tous les services
  - `/status <service>` — état d’un service spécifique
  - `/metrics` — CPU, RAM, disque
  - `/history 24h` — incidents des dernières 24h
  - `/restart <service>` — redémarrer un service (avec confirmation)
- [ ] Authentification par `chat_id`
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

```
neron_control/
├── src/
│   ├── checkers/
│   │   └── neron.py          ✅ Health checks services
│   ├── collectors/
│   │   └── system.py         📋 CPU / RAM / Disque
│   ├── detectors/
│   │   └── anomaly.py        📋 Patterns + seuils dynamiques
│   ├── actions/
│   │   └── corrective.py     📋 Restart / Nettoyage
│   ├── memory/
│   │   └── strategic.py      📋 JSONL mémoire stratégique
│   ├── notifiers/
│   │   └── telegram.py       ✅ Alertes + Bot bidirectionnel (📋)
│   └── database/
│       └── history.py        ✅ Historique SQLite
```

-----

## 📁 Data Layout

```
/mnt/Data/
├── memory/
│   ├── events.jsonl
│   ├── anomalies.jsonl
│   ├── decisions.jsonl
│   └── actions.jsonl
└── logs/
    ├── system.log
    ├── anomalies.log
    ├── decisions.log
    └── actions.log
```

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
