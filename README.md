# Homebox_Neron

# Homebox – Plateforme d’Orchestration Domestique  
**Serveur personnel multi-services basé sur Docker**  
Inclut : Néron (assistant IA local), Home Assistant, Prometheus, Grafana, Nginx Proxy Manager, et autres outils.

---

## 🧠 Présentation du projet

Homebox est une infrastructure centralisée hébergée sur un serveur HP sous Ubuntu.  
Le projet regroupe plusieurs services internes, déployés indépendamment via Docker, avec un focus sur :

- Automatisation (Home Assistant, Node-RED, n8n)
- Monitoring (Prometheus, Grafana, cAdvisor)
- IA locale (Ollama + assistant Néron)
- Reverse proxy sécurisé (Nginx Proxy Manager)
- Services internes modulaires (chaque service → 1 docker-compose)

Néron est l’assistant personnel du système.  
Il s’appuie sur plusieurs briques :

- **neron-core** → API centrale
- **ollama** → moteur LLM local
- **neron-telegram** → interface Telegram
- **node-red** → logique visuelle
- **n8n** → automatisations avancées

---

## 📁 Structure du projet

/homebox
├── .env
├── .gitignore
├── start_neron.sh
├── services/
│ ├── prometheus/
│ ├── grafana/
│ ├── cadvisor/
| |── npm/ (Nginx Proxy Manager)



Chaque service reste autonome et peut être démarré ou modifié sans impacter le reste.

---

## 🚀 Démarrage des services Néron

Depuis `/homebox` :

```bash
bash ./start_neron.sh

Ce script démarre :

Ollama

neron-core

neron-telegram

Node-RED

n8n

Dans l’ordre correct pour éviter les erreurs de dépendances.

git pull
bash start_neron.sh


🛠 Technologies utilisées

Docker / Docker Compose (déploiement modulaire)

Python FastAPI (neron-core)

Node.js (Node-RED, n8n)

Ollama (LLM local)

Telegram Bot API

Prometheus + Grafana (monitoring)

Nginx Proxy Manager (reverse proxy + certificats SSL)

📝 Contributions

Le projet est en évolution continue :
Toute amélioration de la structure, des scripts, ou de l’automatisation est bienvenue.

📄 Licence

Projet privé — utilisation personnelle uniquement.
